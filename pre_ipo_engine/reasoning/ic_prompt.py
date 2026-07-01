def build_ic_prompt(company, financials, valuation, market, deal, computed_facts):
    """
    computed_facts: output of valuation_engine.compute_all_deal_facts().
    Every number in computed_facts is FINAL. Gemini must use these exact
    values and exact units — it must never recompute, re-derive, or
    re-convert them.

    financials: monetary fields are plain floats in INR mn; percentage
    fields are ebitda_margin_pct / revenue_cagr_pct / ebitda_cagr_pct,
    plain floats (e.g. 20.9), formatted with "%" only here at the
    prompt-building step, not upstream.
    """

    def pct(value):
        return f"{value}%" if value is not None else "not available"

    def mn(value):
        return f"₹{value} mn" if value is not None else "not available"

    return f"""
You are a senior Investment Committee member at an Indian PE fund.

COMPANY OVERVIEW
- Sector: {company["sector"]}
- Geography: {company["geography"]}
- Business Model: {company["business_model"]}
- Expansion Plan: {company["expansion_plan"]}
- Management Quality: {company["management_quality"]}

FINANCIAL SNAPSHOT
- Revenue (latest): {mn(financials.get("revenue_latest"))}
- Revenue (forward): {mn(financials.get("revenue_forward"))}
- EBITDA (forward): {mn(financials.get("ebitda_forward"))}
- EBITDA Margin: {pct(financials.get("ebitda_margin_pct"))}
- Revenue CAGR: {pct(financials.get("revenue_cagr_pct"))}
- EBITDA CAGR: {pct(financials.get("ebitda_cagr_pct"))}
- Net Debt: {mn(financials.get("net_debt"))}

MARKET & COMPS
- Industry: {market["industry"]}
- Listed comps: {market["listed_comps"]}
- Trading median multiple: {market["listed_median_multiple"]}x
- Transaction median multiple: {market["transaction_median_multiple"]}x
- Market structure: {market["market_structure"]}

DEAL STRUCTURE (as given)
- Cheque size: ₹{deal["cheque_cr"]} Cr
- Expected ownership: {deal["ownership_pct"]}%
- Primary / Secondary: {deal["type"]}

=== FINAL COMPUTED FIGURES — DO NOT RECALCULATE, DO NOT CONVERT UNITS ===
These figures are authoritative and already account for unit conversion,
multiple selection, and return math. Use them exactly as given, in the
units given. If a section needs a number that is not listed here, state
"not available from provided data" rather than estimating one.

- Company base-case fair value EV: {mn(computed_facts.get("base_case_ev_mn"))} (₹{computed_facts.get("base_case_ev_cr")} Cr)
- Deal-implied post-money EV: {mn(computed_facts.get("post_money_ev_mn"))}
- Deal-implied pre-money EV: {mn(computed_facts.get("pre_money_ev_mn"))}
- Entry multiple (post-money / fwd EBITDA): {computed_facts.get("entry_multiple_post")}x
- Entry multiple (pre-money / fwd EBITDA): {computed_facts.get("entry_multiple_pre")}x
- Discount of deal-implied EV to base-case fair value: {pct(computed_facts.get("discount_to_fair_value_pct"))}
- IPO assumptions used: {computed_facts.get("assumptions_used")}
- Projected EBITDA at IPO: {mn(computed_facts.get("ebitda_at_ipo_mn"))}
- Projected IPO EV — low / base / high: {mn(computed_facts.get("ipo_ev_low_mn"))} / {mn(computed_facts.get("ipo_ev_base_mn"))} / {mn(computed_facts.get("ipo_ev_high_mn"))}
- IPO exit multiples used — low / base / high: {computed_facts.get("ipo_exit_multiple_low")}x / {computed_facts.get("ipo_exit_multiple_base")}x / {computed_facts.get("ipo_exit_multiple_high")}x
- Projected net income at IPO: {mn(computed_facts.get("net_income_at_ipo_mn"))}
- Implied IPO P/E (base case): {computed_facts.get("implied_pe_base")}x
- Upside vs entry — low / base / high: {pct(computed_facts.get("upside_low_pct"))} / {pct(computed_facts.get("upside_base_pct"))} / {pct(computed_facts.get("upside_high_pct"))}
- MOIC — low / base / high: {computed_facts.get("moic_low")}x / {computed_facts.get("moic_base")}x / {computed_facts.get("moic_high")}x
- PRE-DETERMINED RECOMMENDATION TIER: {computed_facts.get("recommendation")}
=========================================================================

TASK:
Prepare a **Pre-IPO Investment Committee Memo** with:
1. State the verdict as exactly: "{computed_facts.get("recommendation")}" — then explain
   the reasoning and conviction level using ONLY the figures above. Do not
   propose a different tier.
2. Valuation reasonableness vs comps — reference the entry multiple and
   discount-to-fair-value figures given above verbatim.
3. Capital structure sanity check
4. Key upside drivers — reference the upside %/MOIC figures above verbatim.
5. Key risks
6. 5-year exit outlook (bear / base / bull) — base case must use the
   IPO EV and multiple figures above; bear/bull may flex narratively but
   must stay directionally consistent with the base case given.

Rules:
- Do NOT invent numbers. Use only the figures provided above.
- Do NOT convert units yourself (no Cr<->mn conversion) — both forms are
  already given where relevant.
- Flag inconsistencies explicitly if you notice any in the input data.
- Write like a real PE IC member.
"""