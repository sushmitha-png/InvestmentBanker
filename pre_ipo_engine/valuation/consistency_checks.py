def check_capital_consistency(valuation_base, cheque_cr, ownership_pct):
    """
    Check consistency between deal structure and valuation.
    Handles None values gracefully.
    """
    if valuation_base is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "Cannot check consistency without valuation data."
        }
    
    if ownership_pct == 0:
        return {
            "status": "INVALID",
            "message": "Ownership percentage cannot be zero."
        }
    
    # Convert cheque_cr (in Cr) to mn, then calculate implied EV
    # 1 Cr = 10 mn
    cheque_mn = cheque_cr * 10
    implied_value = cheque_mn / (ownership_pct / 100)

    if abs(implied_value - valuation_base) / valuation_base > 0.3:
        return {
            "status": "INCONSISTENT",
            "message": f"Cheque size and ownership do not align with valuation. Implied EV: {implied_value:.0f} mn, Base valuation: {valuation_base:.0f} mn"
        }

    return {
        "status": "CONSISTENT",
        "message": f"Deal structure aligns with valuation. Implied EV: {implied_value:.0f} mn"
    }
