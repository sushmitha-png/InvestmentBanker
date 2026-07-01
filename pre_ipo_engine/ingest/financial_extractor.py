import json
import re
from reasoning.gemini import init_gemini, ask_gemini_json

# Global model instance (initialized once)
_model = None

# Conversion rate: 1 USD = 83 INR (adjust as needed)
USD_TO_INR = 83.0

def _get_model(project_id: str = "financial-agent-482306"):
    """Initialize Gemini model if not already done."""
    global _model
    if _model is None:
        _model = init_gemini(project_id)
    return _model

def extract_financials(pdf_text: str, project_id: str = "financial-agent-482306") -> dict:
    """
    Dynamically extract financial metrics from PDF text using Gemini AI.

    Returns a dict with consistent types:
        revenue_latest, revenue_forward, ebitda_forward, net_debt: float or None (INR mn)
        ebitda_margin_pct, revenue_cagr_pct, ebitda_cagr_pct: float or None (plain
            numbers, e.g. 20.9 for "20.9%" — NOT strings, so downstream code never
            has to guess whether it's getting "20.9%" or 20.9)
        currency: "INR" always (converted if needed)
    """
    truncated_text = pdf_text[:10000] if len(pdf_text) > 10000 else pdf_text

    prompt = f"""
You are a financial data extraction specialist. Extract financial metrics from the following company document text.

Extract the following financial metrics and return ONLY valid JSON (no markdown, no explanations):

1. revenue_latest: Latest/actual revenue figure in millions of the ORIGINAL currency (e.g., $230M → 230, ₹1,800Cr → 18000)
2. revenue_forward: Forward/projected revenue in millions of the ORIGINAL currency
3. ebitda_forward: Forward/projected EBITDA in millions of the ORIGINAL currency
4. ebitda_margin: EBITDA margin as a plain number, e.g. 21.2 (NOT a string, NOT "21.2%")
5. net_debt: Net debt in millions of the ORIGINAL currency
6. revenue_cagr: Revenue CAGR as a plain number, e.g. 23 (NOT a string, NOT "23%")
7. ebitda_cagr: EBITDA CAGR as a plain number, e.g. 48 (NOT a string, NOT "48%")
8. currency: The currency used in the document — "USD" if figures use $/USD/US$, "INR" if they use ₹/INR/Rs

Rules:
- Extract numbers ONLY from the text — do NOT estimate or invent values
- If a metric is not found, use null (not 0)
- Convert ALL monetary amounts to millions of the original currency ($230M → 230, ₹1,800Cr → 18000)
- CRITICAL: Detect the currency from symbols/suffixes ($, USD → USD; ₹, INR, Rs → INR)
- All percentage fields (ebitda_margin, revenue_cagr, ebitda_cagr) MUST be plain numbers, not strings, not with a "%" sign
- For margins, calculate if revenue and EBITDA are available: (EBITDA/Revenue)*100
- If CAGR is not explicitly stated, try to infer from revenue/EBITDA growth rates if available

Document Text:
{truncated_text}

Return a JSON object with this exact structure:
{{
    "revenue_latest": <number or null>,
    "revenue_forward": <number or null>,
    "ebitda_forward": <number or null>,
    "ebitda_margin": <number or null>,
    "net_debt": <number or null>,
    "revenue_cagr": <number or null>,
    "ebitda_cagr": <number or null>,
    "currency": "USD" or "INR" or null
}}
"""

    defaults = {
        "revenue_latest": None,
        "revenue_forward": None,
        "ebitda_forward": None,
        "ebitda_margin": None,
        "net_debt": None,
        "revenue_cagr": None,
        "ebitda_cagr": None,
        "currency": None
    }

    try:
        model = _get_model(project_id)
        result = ask_gemini_json(model, prompt)

        # Merge with defaults, keeping extracted values
        financials = {**defaults, **result}

        # --- Normalize every numeric/percentage field to a plain float ---
        # This runs BEFORE currency conversion and BEFORE the margin fallback,
        # so every downstream consumer can always assume float-or-None,
        # never a "21.2%"-style string.
        numeric_keys = [
            "revenue_latest", "revenue_forward", "ebitda_forward", "net_debt",
            "ebitda_margin", "revenue_cagr", "ebitda_cagr",
        ]
        for key in numeric_keys:
            value = financials.get(key)
            if value is None:
                continue
            if isinstance(value, str):
                cleaned = re.sub(r'[^\d.\-]', '', value)
                financials[key] = float(cleaned) if cleaned else None
            else:
                financials[key] = float(value)

        # Calculate ebitda_margin if still missing but revenue/ebitda available.
        # Always stored as a plain float, matching the AI-extracted path.
        if financials["ebitda_margin"] is None and financials["ebitda_forward"] and financials["revenue_forward"]:
            financials["ebitda_margin"] = round(
                (financials["ebitda_forward"] / financials["revenue_forward"]) * 100, 1
            )

        # Convert USD values to INR if needed (monetary fields only —
        # percentage fields are currency-independent and must NOT be touched)
        if financials.get("currency") == "USD":
            for key in ["revenue_latest", "revenue_forward", "ebitda_forward", "net_debt"]:
                if financials[key] is not None:
                    financials[key] = round(financials[key] * USD_TO_INR, 1)
            financials["currency"] = "INR"
        elif financials.get("currency") is None:
            # Default assumption if currency wasn't detected: treat as already INR
            financials["currency"] = "INR"

        # Rename percentage fields explicitly so callers can never confuse
        # them with a string-formatted version. Keep legacy keys too for
        # backwards compatibility with existing callers during migration.
        financials["ebitda_margin_pct"] = financials["ebitda_margin"]
        financials["revenue_cagr_pct"] = financials["revenue_cagr"]
        financials["ebitda_cagr_pct"] = financials["ebitda_cagr"]

        # Log extraction result for traceability
        extracted_fields = [k for k, v in financials.items() if v is not None and k != "currency"]
        print(f"   Extracted {len(extracted_fields)} financial fields: {', '.join(extracted_fields) if extracted_fields else 'NONE'}")
        if financials.get("currency"):
            print(f"   Detected currency: {financials['currency']}")

        return financials

    except Exception as e:
        print(f"   ❌ Error extracting financials: {type(e).__name__}: {e}")
        fallback = {**defaults}
        fallback["ebitda_margin_pct"] = None
        fallback["revenue_cagr_pct"] = None
        fallback["ebitda_cagr_pct"] = None
        fallback["currency"] = "INR"
        return fallback