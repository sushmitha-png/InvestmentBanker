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
from valuation.valuation_engine import compute_valuation
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
        raise ValueError(error_msg)
    
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
        deal["ownership_pct"]
    ) if valuation["base"] else {"status": "INSUFFICIENT_DATA", "message": "Cannot check consistency without valuation."}
    
    # =================================================
    # 🔴 DILIGENCE PROMPT (THIS IS THE INTELLIGENCE CORE)
    # =================================================
    prompt = f"""
You are a senior Investment Committee member and former McKinsey / EY advisor.

Prepare a **Pre-IPO Investment Diligence Report**.
This is NOT a summary. This is a critical diligence document.

====================================================
COMPANY CONTEXT
====================================================
Sector: {company["sector"]}
Geography: {company["geography"]}
Business Model: {company["business_model"]}
Expansion Plan: {company["expansion_plan"]}
Management Quality: {company["management_quality"]}

====================================================
FINANCIAL SNAPSHOT (INR mn)
====================================================
Latest Revenue: {financials.get("revenue_latest", "N/A")}
Forward Revenue: {financials.get("revenue_forward", "N/A")}
Forward EBITDA: {financials.get("ebitda_forward", "N/A")}
EBITDA Margin: {financials.get("ebitda_margin", "N/A")}
Net Debt: {financials.get("net_debt", "N/A")}
Revenue CAGR: {financials.get("revenue_cagr", "N/A")}
EBITDA CAGR: {financials.get("ebitda_cagr", "N/A")}

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

====================================================
MARKET & COMPS
====================================================
Industry: {market["industry"]}
Market Structure: {market["market_structure"]}
Listed Comparables: {", ".join(market["listed_comps"])}
Listed Median Multiple: {market["listed_median_multiple"]}x
Transaction Median Multiple: {market["transaction_median_multiple"]}x

====================================================
VALUATION (EV, INR mn)
====================================================
Low Case: {valuation.get("low", "N/A")}
Base Case: {valuation.get("base", "N/A")}
High Case: {valuation.get("high", "N/A")}

====================================================
DEAL STRUCTURE
====================================================
Cheque Size: ₹{deal["cheque_cr"]} Cr
Target Ownership: {deal["ownership_pct"]}%
Deal Type: {deal["type"]}

Capital Consistency Check:
Status: {consistency.get("status", "UNKNOWN")}
Message: {consistency.get("message", "N/A")}

====================================================
REQUIRED SECTIONS (ALL MUST BE COVERED)
====================================================

**START THE REPORT WITH AN EXECUTIVE SUMMARY DASHBOARD:**

Create a prominent summary section at the very beginning with the following structured format:

## 📊 EXECUTIVE SUMMARY DASHBOARD

### 🎯 INVESTMENT RECOMMENDATION
[Choose ONE: STRONG BUY / BUY / CAUTIOUS BUY / HOLD / PASS]
**Confidence Level:** [High / Medium / Low] (out of 10: [X]/10)

### 💰 VALUATION ASSESSMENT
**Recommended Fair Value (EV):** ₹[X] Cr (INR mn: [X])
**Implied Entry Multiple (EV/EBITDA):** [X]x
**Valuation vs Current Deal:** [Overvalued / Fair / Undervalued] by [X]%

### 📈 IPO PRICE PREDICTION
**Expected IPO Opening P/E Ratio:** [X]x - [Y]x (based on comps at {market["listed_median_multiple"]}x)
**Expected IPO Price Band (per share):** ₹[X] - ₹[Y]
**Upside Potential (if entry at current deal):** [X]% to [Y]%

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
[2-3 sentence summary: Should we proceed? At what valuation? What's the key risk?]

---

Then continue with the detailed sections:
1. Executive Verdict & Conviction (detailed)
2. Investment Thesis – what MUST go right
3. Financial Quality & Sustainability Analysis
4. Growth Quality & Operating Leverage Assessment
5. Valuation & Multiple Justification (include detailed P/E analysis and IPO pricing rationale)
6. Capital Structure & Balance Sheet Risk
7. Business Model Robustness (what breaks under stress)
8. Execution & Expansion Risk
9. Governance & IPO Readiness
10. Downside Scenarios & Fragility Analysis
11. Strategic Optionality (IPO vs M&A vs delay)
12. Key Red Flags (explicit, no soft language)
13. 5-Year Outlook (Bear / Base / Bull) with IPO timeline and pricing scenarios

====================================================
RULES
====================================================
- Use ONLY provided data and analytics
- Do NOT invent numbers, but you CAN provide reasoned estimates for P/E based on comparables
- Be critical, not promotional
- Write as if reviewed by a PE IC and public market investors
- If data is marked as "N/A", acknowledge the limitation in your analysis
- The Executive Summary Dashboard must be clear and actionable
- For P/E prediction, use the listed median multiple ({market["listed_median_multiple"]}x) as a reference and adjust based on company-specific factors
- Provide specific numbers in the summary (not ranges where possible)

End the report with:
--- END OF PRE-IPO DILIGENCE REPORT ---
"""
    
    # =================================================
    # LLM REASONING
    # =================================================
    print("   Generating report with AI...")
    model = init_gemini(project_id)
    memo = ask_gemini(model, prompt)
    
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
    return str(output_path)


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
            report_path = process_pdf(pdf_path)
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
