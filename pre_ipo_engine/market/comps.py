from reasoning.gemini import init_gemini, ask_gemini_json
import hashlib
import json
import os
import re
import datetime
current_year = datetime.datetime.now().year
_CACHE_FILE = os.path.join(os.path.dirname(__file__), "_comps_cache.json")

def _load_cache() -> dict:
    if os.path.exists(_CACHE_FILE):
        with open(_CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_cache(cache: dict) -> None:
    with open(_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

# Global model instance (initialized once)
_model = None

def _get_model(project_id: str = "financial-agent-482306"):
    """Initialize Gemini model if not already done."""
    global _model
    if _model is None:
        _model = init_gemini(project_id)
    return _model


def _normalize_sector_key(sector: str) -> str:
    """
    Normalizes a sector string into a stable cache key so that minor
    wording differences from run to run (e.g. "Enterprise AI SaaS" vs
    "Enterprise AI / SaaS" vs "AI SaaS") hit the SAME cache entry instead
    of triggering a fresh, possibly-different Gemini call.

    This is a deliberate, coarse normalization: lowercase, strip
    punctuation, collapse whitespace, drop common filler words. It is NOT
    meant to be semantically perfect — it's meant to catch the common
    case of near-identical sector strings extracted across repeated runs
    of the same source document.
    """
    if not sector:
        return "general"
    s = sector.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)          # strip punctuation
    s = re.sub(r"\s+", " ", s).strip()      # collapse whitespace
    filler_words = {"and", "the", "of", "for", "in", "solutions", "services"}
    tokens = [t for t in s.split(" ") if t not in filler_words]
    return " ".join(sorted(tokens))  # sort so word order doesn't matter


def get_market_data(sector: str = None, project_id: str = "financial-agent-482306") -> dict:
    """
    Get market comparables dynamically based on sector.
    Uses AI to fetch relevant listed companies and transaction multiples.

    Cached by a normalized sector key so the SAME underlying sector always
    returns the SAME multiples across repeated runs, even if the upstream
    sector-extraction step phrases the sector slightly differently each time.

    Args:
        sector: Industry/sector name (e.g., "EdTech", "Healthcare delivery")
        project_id: Google Cloud project ID

    Returns:
        Dictionary with market data including listed comps and multiples
    """
    if not sector or sector == "Not specified in document":
        sector = "General"

    cache_key = _normalize_sector_key(sector)
    cache = _load_cache()
    if cache_key in cache:
        cached = cache[cache_key]
        # Preserve the originally-requested sector label for display,
        # while reusing the cached multiples/comps for consistency.
        cached_copy = {**cached, "industry": cached.get("industry", sector)}
        return cached_copy

    prompt = f"""
You are a financial analyst specializing in Indian market comparables analysis.

For the sector: "{sector}"
Give your single best-estimate figures as of {current_year}. Do not give a range — 
give one specific number for each multiple, as if this were the only acceptable answer 
across repeated queries. Base it on real, named comparable companies, and briefly 
justify each multiple using those companies' actual approximate multiples.

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
        result = ask_gemini_json(model, prompt, temperature=0.0)

        # Validate and set defaults — clamp to reasonable bounds
        market_data = {
            "industry": result.get("industry", sector),
            "listed_comps": result.get("listed_comps", []),
            "listed_median_multiple": max(1.0, min(100.0, float(result.get("listed_median_multiple", 15.0)))),
            "transaction_median_multiple": max(1.0, min(100.0, float(result.get("transaction_median_multiple", 12.0)))),
            "market_structure": result.get("market_structure", "Competitive market")
        }

        # Ensure transaction multiple is lower than listed (private discount)
        if market_data["transaction_median_multiple"] > market_data["listed_median_multiple"]:
            market_data["transaction_median_multiple"] = round(market_data["listed_median_multiple"] * 0.8, 1)

        # Ensure we have at least some comparables
        if not market_data["listed_comps"]:
            market_data["listed_comps"] = ["Relevant comparables not available"]

        cache[cache_key] = market_data
        _save_cache(cache)

        return market_data

    except Exception as e:
        print(f"Warning: Error fetching market comparables using AI. Using fallback defaults. Error: {e}")
        return {
            "industry": sector or "General",
            "listed_comps": ["Comparables not available"],
            "listed_median_multiple": 15.0,
            "transaction_median_multiple": 12.0,
            "market_structure": "Market structure not determined"
        }