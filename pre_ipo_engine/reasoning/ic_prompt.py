def build_ic_prompt(company, financials, valuation, market, deal):
    return f"""
You are a senior Investment Committee member at an Indian PE fund.

COMPANY OVERVIEW
- Sector: {company["sector"]}
- Geography: {company["geography"]}
- Business Model: {company["business_model"]}
- Expansion Plan: {company["expansion_plan"]}
- Management Quality: {company["management_quality"]}

FINANCIAL SNAPSHOT
- Revenue (latest): INR {financials["revenue_latest"]} mn
- EBITDA (forward): INR {financials["ebitda_forward"]} mn
- EBITDA Margin: {financials["ebitda_margin"]}
- Net Debt: INR {financials["net_debt"]} mn

MARKET & COMPS
- Industry: {market["industry"]}
- Listed comps: {market["listed_comps"]}
- Trading median multiple: {market["listed_median_multiple"]}x
- Transaction median multiple: {market["transaction_median_multiple"]}x
- Market structure: {market["market_structure"]}

VALUATION (EV, INR mn)
- Low: {valuation["low"]}
- Base: {valuation["base"]}
- High: {valuation["high"]}

DEAL STRUCTURE
- Cheque size: ₹{deal["cheque_cr"]} Cr
- Expected ownership: {deal["ownership_pct"]}%
- Primary / Secondary: {deal["type"]}

TASK:
Prepare a **Pre-IPO Investment Committee Memo** with:
1. BUY / HOLD / PASS verdict with conviction
2. Valuation reasonableness vs comps
3. Capital structure sanity check
4. Key upside drivers
5. Key risks
6. 5-year exit outlook (bear / base / bull)

Rules:
- Do NOT invent numbers
- Flag inconsistencies explicitly
- Write like a real PE IC member
"""
