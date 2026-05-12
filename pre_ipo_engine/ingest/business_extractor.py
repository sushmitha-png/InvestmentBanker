from reasoning.gemini import init_gemini, ask_gemini_json

# Global model instance (initialized once)
_model = None

def _get_model(project_id: str = "financial-agent-482306"):
    """Initialize Gemini model if not already done."""
    global _model
    if _model is None:
        _model = init_gemini(project_id)
    return _model

def extract_business_context(pdf_text: str, project_id: str = "financial-agent-482306") -> dict:
    """
    Dynamically extract business context from PDF text using Gemini AI.
    
    Args:
        pdf_text: Extracted text from PDF
        project_id: Google Cloud project ID
        
    Returns:
        Dictionary with business context
    """
    # Limit PDF text to avoid token limits
    truncated_text = pdf_text[:10000] if len(pdf_text) > 10000 else pdf_text
    
    prompt = f"""
You are a business analyst. Extract business context information from the following company document text.

Extract the following information and return ONLY valid JSON (no markdown, no explanations):

1. sector: Industry/sector of the company - use a SIMPLE, STANDARD sector name:
   - For EdTech/Education: "EdTech" or "Education Technology"
   - For Healthcare: "Healthcare" or "Healthcare delivery"
   - For FinTech: "FinTech" or "Financial Technology"
   - For SaaS: "SaaS" or "Software"
   - For E-commerce: "E-commerce" or "Retail"
   - For Manufacturing: "Manufacturing"
   - Use the PRIMARY sector only (e.g., "EdTech", not "EdTech - K12 learning platform")
   
2. geography: Geographic focus/operations (e.g., "North India (Tier-II / III)")
3. business_model: Description of the business model (brief, 1-2 sentences)
4. expansion_plan: Expansion strategy or plans mentioned (brief description)
5. management_quality: Description of management team/leadership (brief description)

Rules:
- Extract information ONLY from the text - do NOT invent or estimate
- For sector, use a SIMPLE, CLEAN sector name (e.g., "EdTech", "Healthcare", "FinTech") - this will be used to find market comparables
- If information is not found, use null
- Keep descriptions concise (1-2 sentences max)
- Be specific and factual
- IMPORTANT: Sector should be a standard industry category name, not a detailed description

Document Text:
{truncated_text}

Return a JSON object with this exact structure:
{{
    "sector": "<sector description>" or null,
    "geography": "<geographic description>" or null,
    "business_model": "<business model description>" or null,
    "expansion_plan": "<expansion plan description>" or null,
    "management_quality": "<management description>" or null
}}
"""

    try:
        model = _get_model(project_id)
        result = ask_gemini_json(model, prompt)
        
        # Validate and set defaults for missing values
        defaults = {
            "sector": None,
            "geography": None,
            "business_model": None,
            "expansion_plan": None,
            "management_quality": None
        }
        
        # Merge with defaults, keeping extracted values
        business_context = {**defaults, **result}
        
        # Set generic defaults if key fields are missing
        if business_context["sector"] is None:
            business_context["sector"] = "Not specified in document"
        if business_context["geography"] is None:
            business_context["geography"] = "Not specified in document"
        if business_context["business_model"] is None:
            business_context["business_model"] = "Not specified in document"
        if business_context["expansion_plan"] is None:
            business_context["expansion_plan"] = "Not specified in document"
        if business_context["management_quality"] is None:
            business_context["management_quality"] = "Not specified in document"
        
        return business_context
        
    except Exception as e:
        print(f"Warning: Error extracting business context using AI. Using fallback defaults. Error: {e}")
        # Fallback to generic defaults
        return {
            "sector": "Not specified in document",
            "geography": "Not specified in document",
            "business_model": "Not specified in document",
            "expansion_plan": "Not specified in document",
            "management_quality": "Not specified in document"
        }
