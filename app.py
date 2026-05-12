import os
import sys
import json
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_pdf_async(job_id, pdf_path, deal, multiple_band, project_id):
    """Process PDF in background thread"""
    try:
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['progress'] = 'Starting analysis...'
        
        report_path = process_pdf(pdf_path, deal, multiple_band, project_id)
        
        # Read the generated report
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['progress'] = 'Analysis complete!'
        jobs[job_id]['report_path'] = report_path
        jobs[job_id]['report_content'] = report_content
        jobs[job_id]['filename'] = os.path.basename(report_path)
        
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['progress'] = f'Error: {str(e)}'
        jobs[job_id]['error'] = str(e)

@app.route('/')
def index():
    """Serve the main frontend page"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle PDF file upload and start processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400
        
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
        
        project_id = request.form.get('project_id', 'financial-agent-482306')
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        file.save(filepath)
        
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
            args=(job_id, filepath, deal, multiple_band, project_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': 'File uploaded successfully. Processing started.'
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
        'filename': job.get('filename', '')
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

