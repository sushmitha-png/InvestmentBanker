# Frontend Web Interface

The Pre-IPO Engine now includes a modern web interface for easy document processing and report generation.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install Flask and other required packages.

### 2. Start the Server

```bash
python app.py
```

The server will start on `http://localhost:5002`

### 3. Open in Browser

Open your web browser and navigate to:
```
http://localhost:5002
```

## 📋 Features

### Document Upload
- Drag and drop or click to upload PDF files
- Support for files up to 50MB
- Real-time file validation

### Configuration
- **Deal Parameters**: Set cheque size, ownership percentage, and deal type
- **Valuation Multiples**: Configure low, base, and high valuation multiples
- **Project ID**: Set your Google Cloud Project ID for Vertex AI

### Real-Time Processing
- Live status updates during processing
- Progress indicators
- Automatic status polling

### Report Viewing
- View generated reports directly in the browser
- Download reports as Markdown files
- Clean, readable formatting

## 🎨 Interface Overview

The web interface consists of:

1. **Upload Section**: File selection and configuration
2. **Status Section**: Real-time processing status and progress
3. **Report Section**: Generated report display with download option

## 🔧 Configuration

### Default Values
- Cheque Size: 350 INR Cr
- Ownership: 11.5%
- Deal Type: Primary
- Valuation Multiples: Low (14x), Base (16x), High (18x)
- Project ID: financial-agent-482306

You can modify these defaults in the HTML form or update them in `templates/index.html`.

## 🌐 API Endpoints

The backend exposes the following REST API endpoints:

- `POST /api/upload` - Upload and process a PDF file
- `GET /api/status/<job_id>` - Get processing status
- `GET /api/report/<job_id>` - Get generated report
- `GET /api/reports` - List all reports
- `GET /api/health` - Health check

## 📁 File Structure

```
Investment_Banker/
├── app.py                  # Flask backend server
├── templates/
│   └── index.html         # Frontend HTML
├── static/
│   ├── css/
│   │   └── style.css     # Styling
│   └── js/
│       └── app.js        # Frontend JavaScript
└── pre_ipo_engine/
    ├── data/             # Uploaded PDFs
    └── outputs/          # Generated reports
```

## 🔒 Security Notes

- File uploads are validated for type and size
- Files are stored with unique identifiers
- For production use, consider:
  - Adding authentication
  - Using a production WSGI server (e.g., Gunicorn)
  - Implementing file cleanup policies
  - Adding rate limiting
  - Using environment variables for sensitive configuration

## 🛠️ Troubleshooting

### Server Won't Start
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check if port 5002 is available
- Verify Python version (3.8+)

### File Upload Fails
- Check file size (max 50MB)
- Verify file is a valid PDF
- Check server logs for errors

### Processing Errors
- Verify Google Cloud authentication: `gcloud auth application-default login`
- Check Project ID is correct
- Ensure Vertex AI API is enabled
- Review server console for detailed error messages

### Reports Not Displaying
- Check browser console for JavaScript errors
- Verify report generation completed successfully
- Try refreshing the page

## 🚀 Production Deployment

For production deployment:

1. Use a production WSGI server:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5002 app:app
```

2. Set environment variables for configuration
3. Use a reverse proxy (nginx) for static files
4. Implement proper authentication and authorization
5. Set up logging and monitoring
6. Configure SSL/TLS certificates

## 💡 Tips

- Keep the browser tab open during processing for real-time updates
- Reports are automatically saved to `pre_ipo_engine/outputs/`
- You can process multiple documents by refreshing and uploading again
- The interface works best on modern browsers (Chrome, Firefox, Safari, Edge)

