def compute_financial_ratios(financials):
    """
    Compute financial ratios from extracted financials.
    Handles None values gracefully.
    """
    ebitda_margin = financials.get("ebitda_margin")
    
    net_debt_to_ebitda = None
    if financials.get("net_debt") is not None and financials.get("ebitda_forward") is not None:
        if financials["ebitda_forward"] > 0:
            net_debt_to_ebitda = round(financials["net_debt"] / financials["ebitda_forward"], 2)
    
    revenue_growth_quality = "Moderate"
    if financials.get("revenue_cagr"):
        # Extract numeric value from percentage string
        try:
            cagr_value = float(financials["revenue_cagr"].replace("%", ""))
            revenue_growth_quality = "High" if cagr_value >= 20 else "Moderate"
        except (ValueError, AttributeError):
            pass
    
    return {
        "ebitda_margin": ebitda_margin,
        "net_debt_to_ebitda": net_debt_to_ebitda,
        "revenue_growth_quality": revenue_growth_quality,
    }
