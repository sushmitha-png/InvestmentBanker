# Dynamic PDF Processing - Implementation Summary

## Overview
The Pre-IPO Engine has been upgraded to dynamically extract real financial and business data from any PDF using AI, instead of using hardcoded values.

## Key Changes

### 1. **Dynamic Financial Extraction** (`ingest/financial_extractor.py`)
- **Before**: Returned hardcoded financial values
- **After**: Uses Gemini AI to extract financial metrics from PDF text
- Extracts: revenue_latest, revenue_forward, ebitda_forward, ebitda_margin, net_debt, revenue_cagr, ebitda_cagr
- Handles missing data gracefully with None values
- Automatically calculates margins when revenue and EBITDA are available

### 2. **Dynamic Business Context Extraction** (`ingest/business_extractor.py`)
- **Before**: Returned hardcoded business context
- **After**: Uses Gemini AI to extract business information from PDF text
- Extracts: sector, geography, business_model, expansion_plan, management_quality
- Provides default values if information is not found

### 3. **Enhanced Gemini Helper** (`reasoning/gemini.py`)
- Added `ask_gemini_json()` function to parse JSON responses from Gemini
- Handles markdown code blocks in responses
- Better error handling for JSON parsing

### 4. **Updated Analytics Modules**
- **financial_ratios.py**: Handles None values, dynamic CAGR parsing
- **growth_quality.py**: Graceful handling of missing data
- **leverage_analysis.py**: Safe division, proper None handling
- **valuation_engine.py**: Returns None values when data is missing

### 5. **Enhanced Main Script** (`run_pre_ipo.py`)
- **Multiple PDF Support**: Can process multiple PDFs in one run
- **Dynamic File Naming**: Output files named after input PDF (e.g., `PreIPO_Diligence_Report_company1.md`)
- **Better Error Handling**: Continues processing other PDFs if one fails
- **Progress Indicators**: Shows what step is being executed
- **Validation**: Checks for missing critical data and warns users

### 6. **Improved Consistency Checks** (`valuation/consistency_checks.py`)
- Better unit conversion handling (Cr to mn)
- More detailed error messages
- Handles None values gracefully

## Usage Examples

### Single PDF
```bash
python run_pre_ipo.py data/company1.pdf
```

### Multiple PDFs
```bash
python run_pre_ipo.py data/company1.pdf data/company2.pdf data/company3.pdf
```

### All PDFs in Directory
```bash
python run_pre_ipo.py data/*.pdf
```

## How It Works

1. **PDF Text Extraction**: Uses `pdfplumber` to extract text
2. **AI Extraction**: Sends text to Gemini AI with specialized prompts for:
   - Financial data extraction (structured JSON response)
   - Business context extraction (structured JSON response)
3. **Data Validation**: Validates extracted data, calculates missing metrics where possible
4. **Analysis**: Runs financial analysis on extracted data
5. **Report Generation**: Uses Gemini to generate comprehensive investment report

## Important Notes

- **API Costs**: Each PDF requires 2-3 Gemini API calls (extraction + report generation)
- **Data Quality**: Extraction quality depends on PDF content clarity
- **Missing Data**: System handles missing data gracefully and notes limitations in reports
- **Project ID**: Update project ID in extractor functions if using different Google Cloud project

## Benefits

✅ Process any PDF without code changes
✅ Real-time data extraction from actual documents
✅ Batch processing capability
✅ Better error handling and user feedback
✅ More accurate analysis based on actual data

