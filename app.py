import os
import sys
import json
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
from dotenv import load_dotenv

load_dotenv()

# Add pre_ipo_engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pre_ipo_engine'))

from run_pre_ipo import process_pdf

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.join('pre_ipo_engine', 'data')
OUTPUT_FOLDER = os.path.join('pre_ipo_engine', 'outputs')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ensure directories exist
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# In-memory job storage (for production, use Redis or database)
jobs = {}

# Track uploaded files by file_id (for reuse in analyze step)
uploaded_files = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_pdf_async(job_id, pdf_path, deal, multiple_band, project_id):
    """Process PDF in background thread"""
    try:
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['progress'] = 'Starting analysis...'
        
        result = process_pdf(pdf_path, deal, multiple_band, project_id)
        if isinstance(result, dict):
            report_path = result['report_path']
            chart_data  = result.get('chart_data', {})
        else:
            report_path = result
            chart_data  = {}

        # Read the generated report
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()

        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['progress'] = 'Analysis complete!'
        jobs[job_id]['report_path'] = report_path
        jobs[job_id]['report_content'] = report_content
        jobs[job_id]['chart_data'] = chart_data
        jobs[job_id]['filename'] = os.path.basename(report_path)
        
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['progress'] = f'Error: {str(e)}'
        jobs[job_id]['error'] = str(e)

@app.route('/')
def index():
    """Serve the main frontend page"""
    return render_template('index.html')

@app.route('/api/extract-companies', methods=['POST'])
def extract_companies_endpoint():
    """Quick scan: upload PDF and extract company names + deal info using Gemini."""
    try:
        from ingest.pdf_loader import load_pdf_text
        from reasoning.gemini import init_gemini, ask_gemini_json

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file.filename or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. PDF only.'}), 400

        # Save the file
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        file.save(filepath)

        # Keep reference so /api/upload can reuse it
        uploaded_files[file_id] = {'filepath': filepath, 'filename': filename}

        # Extract text (first 8k chars is usually enough for company detection)
        pdf_text = load_pdf_text(filepath)
        truncated = pdf_text[:8000] if len(pdf_text) > 8000 else pdf_text

        query = request.form.get('query', '').strip()
        query_hint = (
            f'\nThe investor is specifically looking for a company related to: "{query}". '
            f'Use this to identify the correct primary subject if the PDF is ambiguous.'
            if query else ''
        )

        prompt = f"""You are an analyst reviewing an investor teaser or pre-IPO pitch deck.
            Your task is to identify ONLY the company (or companies) that this document is ABOUT — i.e. the investment target / subject of the pitch.
            DO NOT include companies that are merely referenced as: competitors, customers, investors, logo sources, data citations, market examples, or brands used on slides.{query_hint}

            Rules:
            1. Return the primary subject company first (is_primary: true).
            2. If the document describes multiple DISTINCT variants of what appears to be the same company 
            (e.g. "MetaShot Gaming" and "MetaShot Fitness" operating in genuinely different verticals), 
            list each variant separately so the user can pick the right one.
            3. If there is only one clear subject, return just that one company.
            4. Never include well-known third-party companies (Google, Amazon, Meta, Bloomberg, Deloitte, etc.) 
            unless one of them is literally the company being pitched.

            For each subject company return:
            - name: full official company name
            - sector: industry sector (e.g. EdTech, Healthcare, FinTech, SaaS, Gaming, E-commerce, Manufacturing)
            - description: one sentence about what the company does and its core value proposition
            - is_primary: true for the main subject, false for secondary variants

            Also extract any deal / investment terms explicitly stated in the document:
            - cheque_cr: investment size in INR Crores (number, null if absent)
            - ownership_pct: equity % being offered (number, null if absent)
            - deal_type: "Primary", "Secondary", or "Primary + Secondary" (null if absent)

Document text:
{truncated}

Return ONLY valid JSON — no markdown fences, no explanation:
{{
  "companies": [
    {{"name": "...", "sector": "...", "description": "...", "is_primary": true}}
  ],
  "deal_info": {{
    "cheque_cr": null,
    "ownership_pct": null,
    "deal_type": null
  }}
}}"""

        model = init_gemini()
        result = ask_gemini_json(model, prompt)
        companies = result.get('companies', [])
        # Primary company first
        companies.sort(key=lambda c: 0 if c.get('is_primary') else 1)

        return jsonify({
            'file_id': file_id,
            'filename': filename,
            'filepath': filepath,
            'companies': companies,
            'deal_info': result.get('deal_info', {})
        }), 200

    except Exception as e:
        return jsonify({'error': f'Company extraction failed: {str(e)}'}), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle analysis: accepts either a file_id reference OR a fresh file upload."""
    try:
        file_id_ref = request.form.get('file_id', '').strip()

        if file_id_ref and file_id_ref in uploaded_files:
            # Reuse the file saved during extract-companies
            entry = uploaded_files[file_id_ref]
            filepath = entry['filepath']
            filename = entry['filename']
            if not os.path.exists(filepath):
                return jsonify({'error': 'Uploaded file not found on server. Please re-upload.'}), 400
        else:
            # Fallback: accept a direct file upload
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400
            file_id = str(uuid.uuid4())
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
            file.save(filepath)

        # Get configuration from form data
        deal = {
            'cheque_cr': float(request.form.get('cheque_cr', 350)),
            'ownership_pct': float(request.form.get('ownership_pct', 11.5)),
            'type': request.form.get('deal_type', 'Primary')
        }

        multiple_band = {
            'low': float(request.form.get('multiple_low', 14)),
            'base': float(request.form.get('multiple_base', 16)),
            'high': float(request.form.get('multiple_high', 18))
        }

        # Create job
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            'status': 'queued',
            'progress': 'File uploaded, starting processing...',
            'filename': filename,
            'job_id': job_id
        }

        # Start processing in background thread
        thread = threading.Thread(
            target=process_pdf_async,
            args=(job_id, filepath, deal, multiple_band, 'unused')
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': 'Processing started.'
        }), 202

    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get processing status for a job"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    response = {
        'job_id': job_id,
        'status': job['status'],
        'progress': job.get('progress', ''),
        'filename': job.get('filename', '')
    }
    
    if job['status'] == 'completed':
        response['report_filename'] = job.get('filename', '')
        response['report_path'] = job.get('report_path', '')
    
    if job['status'] == 'error':
        response['error'] = job.get('error', 'Unknown error')
    
    return jsonify(response), 200

@app.route('/api/report/<job_id>', methods=['GET'])
def get_report(job_id):
    """Get the generated report content"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    if job['status'] != 'completed':
        return jsonify({'error': 'Report not ready yet'}), 400
    
    return jsonify({
        'job_id': job_id,
        'report_content': job.get('report_content', ''),
        'filename': job.get('filename', ''),
        'chart_data': job.get('chart_data', {})
    }), 200

@app.route('/api/reports', methods=['GET'])
def list_reports():
    """List all available reports"""
    reports = []
    for job_id, job in jobs.items():
        if job['status'] == 'completed':
            reports.append({
                'job_id': job_id,
                'filename': job.get('filename', ''),
                'original_filename': job.get('original_filename', '')
            })
    return jsonify({'reports': reports}), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    print("Starting Pre-IPO Analysis Server...")
    print("Open http://localhost:5002 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5002)

