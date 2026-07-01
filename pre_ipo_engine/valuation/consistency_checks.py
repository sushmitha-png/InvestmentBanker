from valuation.valuation_engine import compute_deal_implied_valuation


def check_capital_consistency(valuation_base, cheque_cr, ownership_pct, ebitda_forward=None):
    """
    Check consistency between deal structure and valuation.
    Handles None values gracefully.

    NOTE: This now delegates the implied-EV math to
    valuation_engine.compute_deal_implied_valuation() instead of
    recomputing cheque_mn / implied_value independently. Previously this
    file and valuation_engine.py each did their own
    "cheque_mn / (ownership_pct/100)" calculation — same formula, two
    places to drift apart if one is ever edited without the other.
    Now there's a single source of truth.
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

    deal = {"cheque_cr": cheque_cr, "ownership_pct": ownership_pct}
    deal_implied = compute_deal_implied_valuation(deal, ebitda_forward)
    implied_value = deal_implied["post_money_ev_mn"]

    if implied_value is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "Cannot check consistency without deal terms."
        }

    deviation_pct = abs(implied_value - valuation_base) / valuation_base

    if deviation_pct > 0.3:
        return {
            "status": "INCONSISTENT",
            "deviation_pct": round(deviation_pct * 100, 1),
            "message": (
                f"Cheque size and ownership do not align with valuation. "
                f"Implied EV: {implied_value:.0f} mn, Base valuation: {valuation_base:.0f} mn "
                f"({deviation_pct * 100:.1f}% deviation)."
            )
        }

    return {
        "status": "CONSISTENT",
        "deviation_pct": round(deviation_pct * 100, 1),
        "message": f"Deal structure aligns with valuation. Implied EV: {implied_value:.0f} mn"
    }