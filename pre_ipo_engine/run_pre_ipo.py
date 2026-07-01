import sys
import os
from pathlib import Path

# -------------------------------
# INGESTION
# -------------------------------
from ingest.pdf_loader import load_pdf_text
from ingest.financial_extractor import extract_financials
from ingest.business_extractor import extract_business_context

# -------------------------------
# MARKET & VALUATION
# -------------------------------
from market.comps import get_market_data
from valuation.valuation_engine import compute_valuation, compute_all_deal_facts
from valuation.consistency_checks import check_capital_consistency

# -------------------------------
# ANALYTICS (DETERMINISTIC)
# -------------------------------
from analytics.financial_ratios import compute_financial_ratios
from analytics.growth_quality import assess_growth_quality
from analytics.leverage_analysis import analyze_leverage

# -------------------------------
# LLM
# -------------------------------
from reasoning.gemini import init_gemini, ask_gemini
from reasoning.ic_prompt import build_ic_prompt


def process_pdf(pdf_path: str, deal: dict = None, multiple_band: dict = None, project_id: str = "financial-agent-482306"):
    """
    Process a single PDF and generate a Pre-IPO diligence report.

    Args:
        pdf_path: Path to the PDF file
        deal: Deal structure dictionary (optional)
        multiple_band: Valuation multiple band (optional)
        project_id: Google Cloud project ID

    Returns:
        Path to the generated report
    """
    print(f"\n📄 Processing: {pdf_path}")

    # Default deal structure
    if deal is None:
        deal = {
            "cheque_cr": 350,        # INR Cr
            "ownership_pct": 11.5,   # %
            "type": "Primary"
        }

    # Default valuation multiples
    if multiple_band is None:
        multiple_band = {"low": 14, "base": 16, "high": 18}

    # =================================================
    # LOAD & EXTRACT
    # =================================================
    print("   Loading PDF...")
    pdf_text = load_pdf_text(pdf_path)

    if not pdf_text or len(pdf_text.strip()) < 100:
        raise ValueError(f"PDF appears to be empty or could not extract text: {pdf_path}")

    print("   Extracting financial data...")
    financials = extract_financials(pdf_text, project_id)

    # Log extracted currency
    detected_currency = financials.get("currency", "INR")
    print(f"   Detected currency: {detected_currency or 'INR (default)'}")

    print("   Extracting business context...")
    company = extract_business_context(pdf_text, project_id)

    # Validate critical financial data - FAIL EARLY if essential data is missing
    missing_critical_data = []
    if financials.get("revenue_forward") is None:
        missing_critical_data.append("Forward Revenue")
    if financials.get("ebitda_forward") is None:
        missing_critical_data.append("Forward EBITDA")

    if missing_critical_data:
        error_msg = (
            f"Cannot proceed with analysis: Missing critical financial data - {', '.join(missing_critical_data)}. "
            f"The PDF does not contain sufficient financial information to generate a meaningful Pre-IPO diligence report. "
            f"Please ensure the PDF contains forward revenue and EBITDA projections."
        )
        print(f"   ❌ {error_msg}")
        raise ValueError(error_msg)

    # Warn about optional missing fields
    # NOTE: financial_extractor.py now returns ebitda_margin_pct / revenue_cagr_pct /
    # ebitda_cagr_pct (plain floats) instead of ebitda_margin / revenue_cagr / ebitda_cagr
    # (which may have been strings). Both old and new keys are checked here for
    # backwards compatibility during migration.
    optional_missing = []
    if financials.get("revenue_latest") is None:
        optional_missing.append("Revenue (Latest)")
    if financials.get("ebitda_margin_pct", financials.get("ebitda_margin")) is None:
        optional_missing.append("EBITDA Margin")
    if financials.get("revenue_cagr_pct", financials.get("revenue_cagr")) is None:
        optional_missing.append("Revenue CAGR")
    if financials.get("ebitda_cagr_pct", financials.get("ebitda_cagr")) is None:
        optional_missing.append("EBITDA CAGR")
    if optional_missing:
        print(f"   ⚠️  Optional fields not extracted: {', '.join(optional_missing)}")
        print(f"   ⚠️  These will be marked as 'N/A' in the report. Verify manually if critical.")

    # Get market comparables based on extracted sector
    extracted_sector = company.get("sector", "Unknown")
    print(f"   Fetching market comparables for sector: {extracted_sector}...")
    market = get_market_data(sector=extracted_sector, project_id=project_id)

    # Validate sector match
    if market["industry"].lower() != extracted_sector.lower() and extracted_sector != "Not specified in document":
        print(f"   ⚠️  Note: Market comparables fetched for '{market['industry']}' sector")

    # =================================================
    # ANALYTICS (NO LLM INVOLVEMENT)
    # =================================================
    print("   Computing financial ratios...")
    financial_ratios = compute_financial_ratios(financials)
    growth_quality = assess_growth_quality(financials)
    leverage_analysis = analyze_leverage(financials)

    # =================================================
    # VALUATION
    # =================================================
    valuation = compute_valuation(
        financials["ebitda_forward"],
        multiple_band
    )

    consistency = check_capital_consistency(
        valuation["base"],
        deal["cheque_cr"],
        deal["ownership_pct"],
        financials.get("ebitda_forward"),
    ) if valuation["base"] else {"status": "INSUFFICIENT_DATA", "message": "Cannot check consistency without valuation."}

    # =================================================
    # 🔴 DETERMINISTIC DEAL FACTS — computed once, never re-derived by the LLM.
    # This is what previously caused 4 different reports on the same PDF to
    # disagree on entry multiple framing, IPO exit multiple, upside %, MOIC,
    # P/E, fair-value Cr/mn conversion, and recommendation tier. Every one of
    # those numbers now comes from valuation_engine.compute_all_deal_facts()
    # and is injected into the prompt as a fixed fact, not a task.
    #
    # consistency["status"] is now passed straight through to
    # compute_recommendation(), so an INCONSISTENT deal/valuation mismatch
    # (the single biggest red flag across every TechNova sample report)
    # mechanically caps the recommendation tier at CAUTIOUS BUY instead of
    # being left for the LLM to weigh differently run to run.
    # =================================================
    print("   Computing deterministic deal facts (entry multiples, IPO projection, recommendation)...")
    known_risk_flags_count = sum([
        company.get("management_quality") in (None, "Not specified in document", "Unknown"),
        company.get("expansion_plan") not in (None, "Not specified in document") and "expansion" in str(company.get("expansion_plan", "")).lower(),
    ])
    computed_facts = compute_all_deal_facts(
        financials, valuation, market, deal,
        known_risk_flags_count=known_risk_flags_count,
        consistency_status=consistency.get("status"),
    )

    # =================================================
    # 🔴 DILIGENCE PROMPT (THIS IS THE INTELLIGENCE CORE)
    # =================================================
    # build_ic_prompt now injects computed_facts directly and instructs the
    # LLM not to recalculate or re-convert any of them. See reasoning/ic_prompt.py.
    prompt = build_ic_prompt(company, financials, valuation, market, deal, computed_facts)

    # Append the analytics block and the 13-section task list, which remain
    # free-text narrative — the LLM still writes these, but anchored to the
    # fixed figures above rather than inventing its own.
    prompt += f"""

====================================================
PRE-COMPUTED ANALYTICS (FACTS, NOT OPINION)
====================================================
Financial Ratios:
- Net Debt / EBITDA: {financial_ratios.get("net_debt_to_ebitda", "N/A")}
- EBITDA Margin: {financial_ratios.get("ebitda_margin", "N/A")}

Growth Quality:
- Revenue CAGR: {growth_quality.get("revenue_cagr", "N/A")}
- EBITDA CAGR: {growth_quality.get("ebitda_cagr", "N/A")}
- Operating Leverage: {growth_quality.get("operating_leverage", "N/A")}
- Commentary: {growth_quality.get("growth_commentary", "N/A")}

Leverage Analysis:
- Leverage Risk: {leverage_analysis.get("leverage_risk", "N/A")}
- Commentary: {leverage_analysis.get("debt_headroom_comment", "N/A")}

Capital Consistency Check:
Status: {consistency.get("status", "UNKNOWN")}
Message: {consistency.get("message", "N/A")}

====================================================
REQUIRED SECTIONS (ALL MUST BE COVERED)
====================================================

**START THE REPORT WITH AN EXECUTIVE SUMMARY DASHBOARD.**
The dashboard fields below are PRE-FILLED from the FINAL COMPUTED FIGURES
block above. Reproduce them exactly — do not alter the numbers, do not
re-derive them, do not change units.

## 📊 EXECUTIVE SUMMARY DASHBOARD

### 🎯 INVESTMENT RECOMMENDATION
**{computed_facts.get("recommendation")}**
**Confidence Level:** [High / Medium / Low] (out of 10: [X]/10) — your judgment, based on the risk flags below

### 💰 VALUATION ASSESSMENT
**Recommended Fair Value (EV):** ₹{computed_facts.get("base_case_ev_cr")} Cr (INR mn: {computed_facts.get("base_case_ev_mn")})
**Implied Pre-Money Entry Multiple (EV/EBITDA):** {computed_facts.get("entry_multiple_pre")}x
**Implied Post-Money Entry Multiple (EV/EBITDA):** {computed_facts.get("entry_multiple_post")}x
**Valuation vs Current Deal:** Undervalued by {computed_facts.get("discount_to_fair_value_pct")}% (if positive; state "Overvalued" if the figure is negative)

### 📈 IPO PRICE PREDICTION
**Expected IPO Exit Multiple (EV/EBITDA):** {computed_facts.get("ipo_exit_multiple_low")}x - {computed_facts.get("ipo_exit_multiple_high")}x
**Expected IPO Opening P/E Ratio:** ~{computed_facts.get("implied_pe_base")}x (base case)
**Expected IPO Price Band (per share):** Cannot be determined without share count data — state this explicitly, do not estimate.
**Upside Potential (if entry at current deal terms):** {computed_facts.get("upside_low_pct")}% to {computed_facts.get("upside_high_pct")}%

### ✅ KEY DECISION FACTORS
- **Financial Health:** [✅ Strong / ⚠️ Moderate / ❌ Weak]
- **Growth Prospects:** [✅ High / ⚠️ Moderate / ❌ Low]
- **Management Quality:** [✅ Strong / ⚠️ Adequate / ❌ Weak]
- **Market Position:** [✅ Leading / ⚠️ Competitive / ❌ Weak]
- **Valuation Attractiveness:** [✅ Attractive / ⚠️ Fair / ❌ Expensive]
- **IPO Readiness:** [✅ Ready / ⚠️ Needs Work / ❌ Not Ready]

### 🎲 RISK-REWARD ASSESSMENT
**Risk Level:** [Low / Medium / High]
**Reward Potential:** [High / Medium / Low]
**Risk-Reward Ratio:** [Favorable / Balanced / Unfavorable]

### 📋 QUICK VERDICT
[2-3 sentence summary: Should we proceed? At what valuation? What's the key risk? Must be consistent with the {computed_facts.get("recommendation")} tier above.]

---

Then continue with the detailed sections:
1. Executive Verdict & Conviction (detailed)
2. Investment Thesis – what MUST go right
3. Financial Quality & Sustainability Analysis
4. Growth Quality & Operating Leverage Assessment
5. Valuation & Multiple Justification (reference the entry multiples, discount %, IPO exit multiples, P/E, upside %, and MOIC from the FINAL COMPUTED FIGURES block verbatim — do not recompute any of them)
6. Capital Structure & Balance Sheet Risk
7. Business Model Robustness (what breaks under stress)
8. Execution & Expansion Risk
9. Governance & IPO Readiness
10. Downside Scenarios & Fragility Analysis
11. Strategic Optionality (IPO vs M&A vs delay)
12. Key Red Flags (explicit, no soft language)
13. 5-Year Outlook (Bear / Base / Bull) — base case must align directionally with the base-case IPO EV/multiple/upside figures given; bear/bull may flex narratively around them

====================================================
RULES
====================================================
- Use ONLY provided data, analytics, and the FINAL COMPUTED FIGURES block
- Do NOT invent or recompute numbers that are already given above — this
  includes the fair value EV, entry multiples, discount %, IPO exit
  multiples, IPO EV, P/E, upside %, and MOIC. Restate them exactly.
- Do NOT perform any Cr<->mn unit conversion yourself — both forms are
  already given where relevant; just reproduce them.
- Be critical, not promotional
- Write as if reviewed by a PE IC and public market investors
- If data is marked as "N/A" or "not available", acknowledge the
  limitation in your analysis rather than estimating a substitute
- The Executive Summary Dashboard must be clear and actionable
- CRITICAL: When stating an implied entry multiple, explicitly label it
  as "Pre-Money" or "Post-Money"
- CRITICAL: You MUST write ALL 13 detailed sections listed above. Do not
  skip any. Number each section clearly.
- Ensure the report is complete — every section from 1 to 13 must be
  present and substantive before the end marker.

End the report with:
--- END OF PRE-IPO DILIGENCE REPORT ---
"""

    # =================================================
    # LLM REASONING
    # =================================================
    print("   Generating report with AI...")
    model = init_gemini(project_id)
    memo = ask_gemini(model, prompt)

    # Validate report completeness — retry with lower temperature if sections are missing
    required_sections = [f"{i}." for i in range(1, 14)]
    missing = [s for s in required_sections if s not in memo]
    if missing:
        print(f"   ⚠️  Report missing sections: {', '.join(missing)}. Retrying with lower temperature...")
        memo = ask_gemini(model, prompt, temperature=0.1)
        missing = [s for s in required_sections if s not in memo]
        if missing:
            print(f"   ⚠️  Still missing sections after retry: {', '.join(missing)}")
            print(f"   ⚠️  The report may be incomplete. Review manually before distributing.")

    # =================================================
    # 🔴 POST-GENERATION CONSISTENCY VALIDATION
    # Catches the rare case where the LLM still restates a given number
    # incorrectly in prose, despite being told not to recompute it.
    # =================================================
    try:
        from valuation.consistency_checks_post_gen import validate_report_against_facts
        mismatch_warnings = validate_report_against_facts(memo, computed_facts)
        if mismatch_warnings:
            print(f"   ⚠️  Report contains {len(mismatch_warnings)} figure(s) inconsistent with computed facts:")
            for w in mismatch_warnings:
                print(f"      - {w}")
    except ImportError:
        # Validator not yet added to the project — skip silently rather than failing the run.
        pass

    # =================================================
    # OUTPUT (INSTITUTIONAL ARTIFACT)
    # =================================================
    # Generate output filename from input PDF name
    pdf_name = Path(pdf_path).stem
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"PreIPO_Diligence_Report_{pdf_name}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(memo)

    print(f"   ✅ Report generated: {output_path}")

    # Build structured chart data so the frontend can render charts without regex parsing.
    # entry_multiple, revenue_cagr, ebitda_cagr now sourced from computed_facts /
    # the _pct fields where available, falling back to legacy keys.
    revenue_cagr = financials.get("revenue_cagr_pct", financials.get("revenue_cagr"))
    ebitda_cagr = financials.get("ebitda_cagr_pct", financials.get("ebitda_cagr"))
    if revenue_cagr is None and financials.get("revenue_latest") and financials.get("revenue_forward"):
        rev_latest = financials["revenue_latest"]
        rev_forward = financials["revenue_forward"]
        if rev_latest > 0:
            revenue_cagr = round(((rev_forward - rev_latest) / rev_latest) * 100, 1)

    ebitda_margin = financials.get("ebitda_margin_pct", financials.get("ebitda_margin"))

    chart_data = {
        "currency": financials.get("currency", "INR"),
        "provenance": {
            "revenue_latest":   "extracted" if financials.get("revenue_latest") is not None else "unavailable",
            "revenue_forward":  "extracted" if financials.get("revenue_forward") is not None else "unavailable",
            "ebitda_forward":   "extracted" if financials.get("ebitda_forward") is not None else "unavailable",
            "ebitda_margin":    "calculated" if financials.get("ebitda_margin_pct") is not None and financials.get("revenue_forward") else "extracted" if ebitda_margin else "unavailable",
            "net_debt":         "extracted" if financials.get("net_debt") is not None else "unavailable",
            "revenue_cagr":     "calculated" if revenue_cagr and revenue_cagr != financials.get("revenue_cagr_pct") else "extracted" if financials.get("revenue_cagr_pct") else "unavailable",
            "ebitda_cagr":      "extracted" if financials.get("ebitda_cagr_pct") else "unavailable",
            "currency_converted": financials.get("currency") == "INR",
        },
        "valuation": {
            "low":  valuation.get("low"),
            "base": valuation.get("base"),
            "high": valuation.get("high"),
        },
        "financials": {
            "revenue_latest":  financials.get("revenue_latest"),
            "revenue_forward": financials.get("revenue_forward"),
            "ebitda_forward":  financials.get("ebitda_forward"),
            "ebitda_margin":   ebitda_margin,
            "net_debt":        financials.get("net_debt"),
        },
        "growth": {
            "revenue_cagr": revenue_cagr,
            "ebitda_cagr":  ebitda_cagr,
        },
        "market": {
            "listed_multiple":      market.get("listed_median_multiple"),
            "transaction_multiple": market.get("transaction_median_multiple"),
            "entry_multiple":       computed_facts.get("entry_multiple_post"),
        },
        # New: expose the full deterministic deal-facts block to the frontend
        # so it can render IPO projection / upside / MOIC charts without
        # having to regex-parse the generated Markdown report.
        "computed_facts": computed_facts,
    }

    return {"report_path": str(output_path), "chart_data": chart_data}


# =================================================
# ENTRY
# =================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pre_ipo.py <pdf_file1> [pdf_file2] ... [pdf_fileN]")
        print("   or: python run_pre_ipo.py data/*.pdf  (process all PDFs in data folder)")
        sys.exit(1)

    pdf_paths = sys.argv[1:]

    # Expand glob patterns if needed
    import glob
    expanded_paths = []
    for path in pdf_paths:
        if '*' in path or '?' in path:
            expanded_paths.extend(glob.glob(path))
        else:
            expanded_paths.append(path)

    if not expanded_paths:
        print("Error: No PDF files found.")
        sys.exit(1)

    # Process each PDF
    generated_reports = []
    for pdf_path in expanded_paths:
        if not os.path.exists(pdf_path):
            print(f"⚠️  Warning: File not found: {pdf_path}")
            continue

        if not pdf_path.lower().endswith('.pdf'):
            print(f"⚠️  Warning: Not a PDF file: {pdf_path}")
            continue

        try:
            result = process_pdf(pdf_path)
            report_path = result["report_path"] if isinstance(result, dict) else result
            generated_reports.append(report_path)
        except Exception as e:
            print(f"❌ Error processing {pdf_path}: {e}")
            continue

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Processing complete! Generated {len(generated_reports)} report(s):")
    for report in generated_reports:
        print(f"   - {report}")
    print(f"{'='*60}\n")