import json
import re
from reasoning.gemini import init_gemini, ask_gemini_json

# Global model instance (initialized once)
_model = None

def _get_model(project_id: str = "financial-agent-482306"):
    """Initialize Gemini model if not already done."""
    global _model
    if _model is None:
        _model = init_gemini(project_id)
    return _model

def extract_financials(pdf_text: str, project_id: str = "financial-agent-482306") -> dict:
    """
    Dynamically extract financial metrics from PDF text using Gemini AI.
    
    Args:
        pdf_text: Extracted text from PDF
        project_id: Google Cloud project ID
        
    Returns:
        Dictionary with financial metrics
    """
    # Limit PDF text to avoid token limits (use first 10000 chars, typically enough for financial summary)
    truncated_text = pdf_text[:10000] if len(pdf_text) > 10000 else pdf_text
    
    prompt = f"""
You are a financial data extraction specialist. Extract financial metrics from the following company document text.

Extract the following financial metrics and return ONLY valid JSON (no markdown, no explanations):

1. revenue_latest: Latest/actual revenue figure (in millions, numeric only, no currency symbols)
2. revenue_forward: Forward/projected revenue (in millions, numeric only)
3. ebitda_forward: Forward/projected EBITDA (in millions, numeric only)
4. ebitda_margin: EBITDA margin as percentage (string format like "21.2%")
5. net_debt: Net debt amount (in millions, numeric only)
6. revenue_cagr: Revenue CAGR as percentage (string format like "23%")
7. ebitda_cagr: EBITDA CAGR as percentage (string format like "48%")

Rules:
- Extract numbers ONLY from the text - do NOT estimate or invent values
- If a metric is not found, use null (not 0)
- Convert all amounts to millions (INR mn)
- For percentages, extract the actual percentage or calculate if historical data is available
- If CAGR is not explicitly stated, try to infer from revenue/EBITDA growth rates if available
- For margins, calculate if revenue and EBITDA are available: (EBITDA/Revenue)*100

Document Text:
{truncated_text}

Return a JSON object with this exact structure:
{{
    "revenue_latest": <number or null>,
    "revenue_forward": <number or null>,
    "ebitda_forward": <number or null>,
    "ebitda_margin": "<percentage>" or null,
    "net_debt": <number or null>,
    "revenue_cagr": "<percentage>" or null,
    "ebitda_cagr": "<percentage>" or null
}}
"""

    try:
        model = _get_model(project_id)
        result = ask_gemini_json(model, prompt)
        
        # Validate and set defaults for missing values
        defaults = {
            "revenue_latest": None,
            "revenue_forward": None,
            "ebitda_forward": None,
            "ebitda_margin": None,
            "net_debt": None,
            "revenue_cagr": None,
            "ebitda_cagr": None
        }
        
        # Merge with defaults, keeping extracted values
        financials = {**defaults, **result}
        
        # Calculate ebitda_margin if not provided but we have revenue and ebitda
        if financials["ebitda_margin"] is None and financials["ebitda_forward"] and financials["revenue_forward"]:
            margin = (financials["ebitda_forward"] / financials["revenue_forward"]) * 100
            financials["ebitda_margin"] = f"{margin:.1f}%"
        
        # Convert numeric strings to numbers where needed
        for key in ["revenue_latest", "revenue_forward", "ebitda_forward", "net_debt"]:
            if financials[key] is not None:
                if isinstance(financials[key], str):
                    # Remove commas, currency symbols, and convert
                    financials[key] = float(re.sub(r'[^\d.]', '', financials[key]))
        
        return financials
        
    except Exception as e:
        print(f"Warning: Error extracting financials using AI. Using fallback defaults. Error: {e}")
        # Fallback to default structure with None values
        return {
            "revenue_latest": None,
            "revenue_forward": None,
            "ebitda_forward": None,
            "ebitda_margin": None,
            "net_debt": None,
            "revenue_cagr": None,
            "ebitda_cagr": None
        }
