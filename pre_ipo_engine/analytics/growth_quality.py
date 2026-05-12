def assess_growth_quality(financials):
    """
    Assess growth quality from extracted financials.
    Handles None values gracefully.
    """
    revenue_cagr = financials.get("revenue_cagr")
    ebitda_cagr = financials.get("ebitda_cagr")
    
    operating_leverage = "Moderate"
    if revenue_cagr and ebitda_cagr:
        try:
            revenue_val = float(str(revenue_cagr).replace("%", ""))
            ebitda_val = float(str(ebitda_cagr).replace("%", ""))
            operating_leverage = "Strong" if ebitda_val > revenue_val * 1.5 else "Moderate"
        except (ValueError, AttributeError):
            pass
    
    growth_commentary = "EBITDA growing faster than revenue indicates operating leverage."
    if not revenue_cagr or not ebitda_cagr:
        growth_commentary = "Insufficient data to assess operating leverage."
    
    return {
        "revenue_cagr": revenue_cagr,
        "ebitda_cagr": ebitda_cagr,
        "operating_leverage": operating_leverage,
        "growth_commentary": growth_commentary
    }
