def analyze_leverage(financials):
    """
    Analyze leverage from extracted financials.
    Handles None values gracefully.
    """
    net_debt = financials.get("net_debt")
    ebitda_forward = financials.get("ebitda_forward")
    
    if net_debt is None or ebitda_forward is None or ebitda_forward == 0:
        return {
            "net_debt_to_ebitda": None,
            "leverage_risk": "Unknown",
            "debt_headroom_comment": "Insufficient data to assess leverage."
        }
    
    nd_ebitda = net_debt / ebitda_forward
    risk = "Low" if nd_ebitda < 2 else "Moderate" if nd_ebitda < 3 else "High"

    return {
        "net_debt_to_ebitda": round(nd_ebitda, 2),
        "leverage_risk": risk,
        "debt_headroom_comment": "Balance sheet has significant capacity for expansion capex." if risk == "Low" else "Leverage levels are manageable." if risk == "Moderate" else "Monitor leverage levels closely."
    }
