from reasoning.gemini import init_gemini, ask_gemini_json

# Global model instance (initialized once)
_model = None

def _get_model(project_id: str = "financial-agent-482306"):
    """Initialize Gemini model if not already done."""
    global _model
    if _model is None:
        _model = init_gemini(project_id)
    return _model

def get_market_data(sector: str = None, project_id: str = "financial-agent-482306") -> dict:
    """
    Get market comparables dynamically based on sector.
    Uses AI to fetch relevant listed companies and transaction multiples.
    
    Args:
        sector: Industry/sector name (e.g., "EdTech", "Healthcare delivery")
        project_id: Google Cloud project ID
        
    Returns:
        Dictionary with market data including listed comps and multiples
    """
    # If no sector provided, use a generic default (shouldn't happen in practice)
    if not sector or sector == "Not specified in document":
        sector = "General"
    
    prompt = f"""
You are a financial analyst specializing in Indian market comparables analysis.

For the sector/industry: "{sector}"

Provide relevant market comparables data. Return ONLY valid JSON (no markdown, no explanations):

1. industry: The sector/industry name (use the provided sector: "{sector}")
2. listed_comps: List of 3-5 relevant publicly listed Indian companies in this sector (company names only, as array)
3. listed_median_multiple: Typical EV/EBITDA multiple for listed companies in this sector (number, e.g., 15.5)
4. transaction_median_multiple: Typical EV/EBITDA multiple for private/PE transactions in this sector (number, typically 20-30% lower than listed, e.g., 12.0)
5. market_structure: Brief description of market structure (e.g., "Fragmented but consolidating", "Oligopolistic", "Highly competitive")

Rules:
- Use real, well-known Indian listed companies in this sector
- Multiples should be realistic based on the sector (EdTech: 8-15x, Healthcare: 20-25x, FinTech: 12-20x, etc.)
- Transaction multiples are typically 20-30% lower than listed multiples for private deals
- If sector is unclear, use broader industry classification

Return a JSON object with this exact structure:
{{
    "industry": "<sector name>",
    "listed_comps": ["Company 1", "Company 2", "Company 3"],
    "listed_median_multiple": <number>,
    "transaction_median_multiple": <number>,
    "market_structure": "<description>"
}}
"""

    try:
        model = _get_model(project_id)
        result = ask_gemini_json(model, prompt)
        
        # Validate and set defaults
        market_data = {
            "industry": result.get("industry", sector),
            "listed_comps": result.get("listed_comps", []),
            "listed_median_multiple": result.get("listed_median_multiple", 15.0),
            "transaction_median_multiple": result.get("transaction_median_multiple", 12.0),
            "market_structure": result.get("market_structure", "Competitive market")
        }
        
        # Ensure we have at least some comparables
        if not market_data["listed_comps"]:
            market_data["listed_comps"] = ["Relevant comparables not available"]
        
        return market_data
        
    except Exception as e:
        print(f"Warning: Error fetching market comparables using AI. Using fallback defaults. Error: {e}")
        # Fallback to generic defaults
        return {
            "industry": sector or "General",
            "listed_comps": ["Comparables not available"],
            "listed_median_multiple": 15.0,
            "transaction_median_multiple": 12.0,
            "market_structure": "Market structure not determined"
        }
