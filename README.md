# Pre-IPO Investment Diligence Engine

An AI-powered investment banking tool that generates comprehensive Pre-IPO diligence reports for investment committees. This system extracts financial data from company PDFs, performs financial analysis, and uses Google's Gemini AI to create institutional-grade investment memorandums.

## 🎯 What This Project Does

The Pre-IPO Engine automates the creation of investment diligence reports by:

1. **Ingesting** company financial documents (PDFs)
2. **Extracting** financial metrics and business context
3. **Analyzing** financial ratios, growth quality, and leverage
4. **Valuing** the company using market comparables
5. **Generating** a comprehensive investment committee report using Google Gemini AI

The output is a professional, critical analysis report covering 13 key sections including valuation justification, risk analysis, and strategic optionality.

## 📁 Project Structure

```
pre_ipo_engine/
├── ingest/              # Data ingestion modules
│   ├── pdf_loader.py           # PDF text extraction
│   ├── financial_extractor.py  # Financial metrics extraction
│   └── business_extractor.py   # Business context extraction
├── analytics/           # Financial analysis modules
│   ├── financial_ratios.py     # Ratio calculations
│   ├── growth_quality.py       # Growth analysis
│   └── leverage_analysis.py    # Leverage assessment
├── market/              # Market data modules
│   └── comps.py                # Comparable companies data
├── valuation/           # Valuation modules
│   ├── valuation_engine.py     # EV calculations
│   └── consistency_checks.py   # Deal consistency validation
├── reasoning/           # AI/LLM integration
│   ├── gemini.py               # Google Vertex AI integration
│   └── ic_prompt.py            # Investment committee prompts
├── outputs/             # Generated reports
│   └── PreIPO_Diligence_Report.md
├── data/                # Input PDF files
│   └── test.pdf
└── run_pre_ipo.py       # Main entry point
```

## 🔧 Prerequisites

1. **Python 3.8+** (Python 3.13 is being used in this project)
2. **Google Cloud Account** with Vertex AI API enabled
3. **Google Cloud Project ID** (currently hardcoded as `"financial-agent-482306"`)

## 📦 Installation

### 1. Activate Virtual Environment

A virtual environment is already set up in the `venv/` directory. Activate it:

```bash
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

The project requires the following Python packages:

```bash
pip install pdfplumber google-cloud-aiplatform
```

Or if you have a requirements file (recommended to create one):

```bash
pip install -r requirements.txt
```

**Key Dependencies:**
- `pdfplumber`: PDF text extraction
- `google-cloud-aiplatform`: Google Vertex AI (Gemini) integration

### 3. Set Up Google Cloud Authentication

You need to authenticate with Google Cloud to use Vertex AI. Choose one method:

**Option A: Application Default Credentials (Recommended)**
```bash
gcloud auth application-default login
```

**Option B: Service Account Key**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

### 4. Enable Vertex AI API

Make sure the Vertex AI API is enabled in your Google Cloud project:

```bash
gcloud services enable aiplatform.googleapis.com --project=financial-agent-482306
```

Or enable it via the [Google Cloud Console](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com).

### 5. Update Project ID (if needed)

If you're using a different Google Cloud project, update the project ID in `pre_ipo_engine/reasoning/gemini.py`:

```python
model = init_gemini("your-project-id")  # Line 189 in run_pre_ipo.py
```

## 🌐 Web Interface (Recommended)

The easiest way to use the Pre-IPO Engine is through the web interface:

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Start the web server
python app.py
```

Then open your browser to `http://localhost:5002`

The web interface provides:
- Easy PDF upload
- Configuration of deal parameters and valuation multiples
- Real-time processing status
- Report viewing and download

See [FRONTEND_README.md](FRONTEND_README.md) for detailed frontend documentation.

## 🚀 Running the Project

### Command Line Usage

**Process a single PDF:**
```bash
cd pre_ipo_engine
python run_pre_ipo.py data/test.pdf
```

**Process multiple PDFs:**
```bash
python run_pre_ipo.py data/company1.pdf data/company2.pdf data/company3.pdf
```

**Process all PDFs in a directory:**
```bash
python run_pre_ipo.py data/*.pdf
```

### What Happens When You Run

1. **PDF Loading**: Extracts text from the provided PDF(s)
2. **AI-Powered Data Extraction**: Uses Gemini AI to extract:
   - Financial metrics (revenue, EBITDA, margins, debt, CAGR)
   - Business context (sector, geography, business model, expansion plans, management)
3. **Analysis**: Computes financial ratios, growth quality, and leverage metrics
4. **Valuation**: Calculates enterprise value using EBITDA multiples
5. **AI Generation**: Uses Gemini to generate a comprehensive investment report
6. **Output**: Writes individual reports to `outputs/PreIPO_Diligence_Report_<filename>.md` for each PDF

### Output

The generated report includes 13 sections:
1. Executive Verdict & Conviction
2. Investment Thesis
3. Financial Quality & Sustainability Analysis
4. Growth Quality & Operating Leverage Assessment
5. Valuation & Multiple Justification
6. Capital Structure & Balance Sheet Risk
7. Business Model Robustness
8. Execution & Expansion Risk
9. Governance & IPO Readiness
10. Downside Scenarios & Fragility Analysis
11. Strategic Optionality
12. Key Red Flags
13. 5-Year Outlook (Bear / Base / Bull)

## ⚙️ Configuration

### Deal Parameters

You can customize the deal structure in `run_pre_ipo.py` (lines 52-56):

```python
deal = {
    "cheque_cr": 350,        # INR Cr
    "ownership_pct": 11.5,   # %
    "type": "Primary"
}
```

### Valuation Multiples

Adjust the valuation multiple band (lines 70-71):

```python
multiple_band = {"low": 14, "base": 16, "high": 18}
```

### Financial Data

Currently, financial data is hardcoded in:
- `ingest/financial_extractor.py` - Financial metrics
- `ingest/business_extractor.py` - Business context
- `market/comps.py` - Market comparables

To use real extraction, you'll need to implement parsing logic in these files.

## 🔍 Example Workflow

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Ensure authentication
gcloud auth application-default login

# 3. Run the analysis
cd pre_ipo_engine
python run_pre_ipo.py data/test.pdf

# 4. View the generated report
cat outputs/PreIPO_Diligence_Report.md
```

## 🎯 Dynamic PDF Processing

The system now **dynamically extracts data from any PDF** using AI:

- **Financial Extraction**: Automatically extracts revenue, EBITDA, margins, debt, and growth metrics from PDF text
- **Business Context**: Extracts sector, geography, business model, expansion plans, and management information
- **Smart Parsing**: Uses Google Gemini AI to understand and extract structured data from unstructured PDF text
- **Multiple PDFs**: Process multiple companies at once - each PDF generates its own report

### How It Works

1. PDF text is extracted using `pdfplumber`
2. Text is analyzed by Gemini AI with specialized prompts for financial and business data extraction
3. Extracted data is validated and used for analysis
4. If data is missing, the system handles it gracefully and notes limitations in the report

## 📝 Notes

- **AI-Powered Extraction**: The system uses Gemini AI to extract data, so extraction quality depends on PDF content clarity
- **Google Cloud Costs**: Using Vertex AI (Gemini) incurs API costs. Each PDF requires 2-3 API calls (extraction + report generation). Check [Google Cloud Pricing](https://cloud.google.com/vertex-ai/pricing) for details.
- **Project ID**: The project ID is currently hardcoded as `"financial-agent-482306"`. Update it in the extractor functions or `run_pre_ipo.py` if using a different project.
- **Data Quality**: For best results, ensure PDFs contain clear financial statements and company information. Scanned PDFs may have lower extraction accuracy.

## 🛠️ Troubleshooting

### Authentication Errors
- Ensure you're authenticated: `gcloud auth application-default login`
- Check that your Google Cloud project ID is correct
- Verify the Vertex AI API is enabled in your project

### Import Errors
- Make sure the virtual environment is activated
- Install missing packages: `pip install pdfplumber google-cloud-aiplatform`

### API Errors
- Check your Google Cloud billing is enabled
- Verify the Vertex AI API is enabled for your project
- Ensure you have the necessary IAM permissions

## 📄 License

This project appears to be for internal/educational use. Please check with the project owner for licensing details.

