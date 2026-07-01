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


# ---------------------------------------------------------------------------
# Unit conversion helpers — single source of truth, never let the LLM do this
# ---------------------------------------------------------------------------

def cr_to_mn(cr):
    if cr is None:
        return None
    return round(cr * 10, 2)


def mn_to_cr(mn):
    if mn is None:
        return None
    return round(mn / 10, 2)


# ---------------------------------------------------------------------------
# Deal-implied valuation (previously invented by Gemini every run)
# ---------------------------------------------------------------------------

def compute_deal_implied_valuation(deal, ebitda_forward):
    """
    Computes post-money / pre-money EV implied by the deal terms,
    and the resulting entry multiples. All in INR mn for consistency
    with the rest of the financial stack (financial_extractor.py returns
    monetary fields in INR mn).
    """
    cheque_cr = deal.get("cheque_cr")
    ownership_pct = deal.get("ownership_pct")

    if cheque_cr is None or ownership_pct is None or ownership_pct == 0:
        return {
            "cheque_mn": None,
            "post_money_ev_mn": None,
            "pre_money_ev_mn": None,
            "entry_multiple_post": None,
            "entry_multiple_pre": None,
        }

    cheque_mn = cr_to_mn(cheque_cr)
    post_money_ev_mn = round(cheque_mn / (ownership_pct / 100), 1)
    pre_money_ev_mn = round(post_money_ev_mn - cheque_mn, 1)

    entry_multiple_post = None
    entry_multiple_pre = None
    if ebitda_forward:
        entry_multiple_post = round(post_money_ev_mn / ebitda_forward, 1)
        entry_multiple_pre = round(pre_money_ev_mn / ebitda_forward, 1)

    return {
        "cheque_mn": cheque_mn,
        "post_money_ev_mn": post_money_ev_mn,
        "pre_money_ev_mn": pre_money_ev_mn,
        "entry_multiple_post": entry_multiple_post,
        "entry_multiple_pre": entry_multiple_pre,
    }


# ---------------------------------------------------------------------------
# Discount-to-fair-value (previously stated inconsistently: 52%, 52.3%, 57%)
# ---------------------------------------------------------------------------

def compute_discount_to_fair_value(post_money_ev_mn, base_case_ev_mn):
    if not post_money_ev_mn or not base_case_ev_mn:
        return None
    return round((1 - post_money_ev_mn / base_case_ev_mn) * 100, 1)


# ---------------------------------------------------------------------------
# IPO exit projection — fixed assumptions, not Gemini's choice per run
# ---------------------------------------------------------------------------

# Centralized, versioned assumptions. Change these in ONE place if the
# IC wants different scenario assumptions — never let the LLM choose them.
IPO_ASSUMPTIONS = {
    "years_to_ipo": 2,
    "ebitda_cagr_assumed_pct": 30.0,   # conservative vs historical extracted CAGR, fixed
    "tax_rate_pct": 25.0,
    "da_pct_of_revenue": 5.0,
}


def project_ipo_exit(ebitda_forward, revenue_forward, market, post_money_ev_mn,
                      assumptions=None):
    """
    Deterministically projects EBITDA at IPO, IPO EV (low/base/high using
    transaction median -> listed median as the range), implied P/E, and
    upside / MOIC vs the deal-implied post-money entry EV.

    market: dict from comps.get_market_data(), expects
        listed_median_multiple, transaction_median_multiple (floats).
    """
    a = assumptions or IPO_ASSUMPTIONS

    if ebitda_forward is None or post_money_ev_mn is None:
        return None

    years = a["years_to_ipo"]
    growth = 1 + a["ebitda_cagr_assumed_pct"] / 100

    ebitda_at_ipo = round(ebitda_forward * (growth ** years), 1)

    low_mult = market["transaction_median_multiple"]
    high_mult = market["listed_median_multiple"]
    base_mult = round((low_mult + high_mult) / 2, 1)

    ipo_ev_low = round(ebitda_at_ipo * low_mult, 1)
    ipo_ev_base = round(ebitda_at_ipo * base_mult, 1)
    ipo_ev_high = round(ebitda_at_ipo * high_mult, 1)

    # Net income bridge — fixed methodology, not re-invented per run
    da_mn = None
    net_income_at_ipo = None
    if revenue_forward is not None:
        da_mn = round(revenue_forward * a["da_pct_of_revenue"] / 100, 1)
        ebit_at_ipo = ebitda_at_ipo - da_mn
        net_income_at_ipo = round(ebit_at_ipo * (1 - a["tax_rate_pct"] / 100), 1)

    implied_pe_base = None
    if net_income_at_ipo and net_income_at_ipo > 0:
        implied_pe_base = round(ipo_ev_base / net_income_at_ipo, 1)

    upside_low_pct = round((ipo_ev_low / post_money_ev_mn - 1) * 100, 1)
    upside_base_pct = round((ipo_ev_base / post_money_ev_mn - 1) * 100, 1)
    upside_high_pct = round((ipo_ev_high / post_money_ev_mn - 1) * 100, 1)

    moic_low = round(ipo_ev_low / post_money_ev_mn, 2)
    moic_base = round(ipo_ev_base / post_money_ev_mn, 2)
    moic_high = round(ipo_ev_high / post_money_ev_mn, 2)

    return {
        "assumptions_used": a,
        "ebitda_at_ipo_mn": ebitda_at_ipo,
        "ipo_exit_multiple_low": low_mult,
        "ipo_exit_multiple_base": base_mult,
        "ipo_exit_multiple_high": high_mult,
        "ipo_ev_low_mn": ipo_ev_low,
        "ipo_ev_base_mn": ipo_ev_base,
        "ipo_ev_high_mn": ipo_ev_high,
        "net_income_at_ipo_mn": net_income_at_ipo,
        "implied_pe_base": implied_pe_base,
        "upside_low_pct": upside_low_pct,
        "upside_base_pct": upside_base_pct,
        "upside_high_pct": upside_high_pct,
        "moic_low": moic_low,
        "moic_base": moic_base,
        "moic_high": moic_high,
    }


# ---------------------------------------------------------------------------
# Recommendation tier — deterministic rule, LLM only justifies it
# ---------------------------------------------------------------------------

def compute_recommendation(discount_to_fair_value_pct, known_risk_flags_count,
                            ebitda_margin_pct=None, consistency_status=None):
    """
    Deterministic recommendation tier so the same inputs ALWAYS produce
    the same verdict. The LLM's job is to explain this, not decide it.

    consistency_status: optional "status" field from
        consistency_checks.check_capital_consistency(). A deal whose
        terms imply an EV more than 30% off the company's own base case
        is the single largest red flag possible, and should mechanically
        cap the recommendation tier rather than be left for the LLM to
        weigh inconsistently from run to run.
    """
    if discount_to_fair_value_pct is None:
        return "INSUFFICIENT DATA"

    if consistency_status == "INCONSISTENT":
        return "CAUTIOUS BUY"

    if discount_to_fair_value_pct >= 40 and known_risk_flags_count <= 2:
        return "STRONG BUY"
    elif discount_to_fair_value_pct >= 20:
        return "BUY"
    elif discount_to_fair_value_pct >= 0:
        return "CAUTIOUS BUY"
    else:
        return "HOLD / PASS"


# ---------------------------------------------------------------------------
# Master function — call this once, pass the whole dict into the prompt
# ---------------------------------------------------------------------------

def compute_all_deal_facts(financials, valuation, market, deal,
                            known_risk_flags_count=2, consistency_status=None):
    """
    Single entry point: computes every number that previously varied
    across LLM runs, and returns them as a flat, prompt-ready dict.

    financials: dict from financial_extractor.extract_financials() —
        monetary fields are plain floats in INR mn; ebitda_margin_pct /
        revenue_cagr_pct / ebitda_cagr_pct are plain floats (e.g. 20.9),
        never strings with a "%" sign.
    valuation: dict from compute_valuation() — {"low", "base", "high"} in INR mn.
    market: dict from comps.get_market_data().
    deal: dict — {"cheque_cr", "ownership_pct", "type"}.
    consistency_status: optional "status" string from
        consistency_checks.check_capital_consistency(), used to cap the
        recommendation tier when the deal terms and base-case valuation
        are flagged as INCONSISTENT.
    """
    ebitda_forward = financials.get("ebitda_forward")
    revenue_forward = financials.get("revenue_forward")
    base_case_ev_mn = valuation.get("base")

    deal_implied = compute_deal_implied_valuation(deal, ebitda_forward)
    discount_pct = compute_discount_to_fair_value(
        deal_implied["post_money_ev_mn"], base_case_ev_mn
    )
    ipo_projection = project_ipo_exit(
        ebitda_forward, revenue_forward, market,
        deal_implied["post_money_ev_mn"]
    )
    recommendation = compute_recommendation(
        discount_pct, known_risk_flags_count,
        ebitda_margin_pct=financials.get("ebitda_margin_pct"),
        consistency_status=consistency_status,
    )

    facts = {
        "base_case_ev_mn": base_case_ev_mn,
        "base_case_ev_cr": mn_to_cr(base_case_ev_mn),
        "discount_to_fair_value_pct": discount_pct,
        "recommendation": recommendation,
        **deal_implied,
        "cheque_cr": deal.get("cheque_cr"),
    }
    if ipo_projection:
        facts.update(ipo_projection)

    return facts