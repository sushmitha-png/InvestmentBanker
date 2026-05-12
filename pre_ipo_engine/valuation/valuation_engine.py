def compute_valuation(ebitda_forward, multiple_band):
    """
    Compute valuation from EBITDA and multiple band.
    Handles None values gracefully.
    """
    if ebitda_forward is None:
        return {
            "low": None,
            "base": None,
            "high": None,
        }
    
    return {
        "low": round(ebitda_forward * multiple_band["low"]),
        "base": round(ebitda_forward * multiple_band["base"]),
        "high": round(ebitda_forward * multiple_band["high"]),
    }
