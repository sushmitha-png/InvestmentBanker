import re


def validate_report_against_facts(report_markdown, computed_facts, tolerance_pct=0.5):
    """
    Scans the generated report for the key dashboard figures and confirms
    they match computed_facts. Returns a list of mismatch warnings (empty
    list = clean). This is a safety net for cases where the LLM restates
    a correct input incorrectly in prose, despite being given the final
    figure directly.

    tolerance_pct: allowed relative deviation (e.g. due to independent
    rounding in different parts of the report) before flagging.
    """
    warnings = []

    def find_numbers_near(label_patterns):
        """Find numeric values near any of the given regex label patterns."""
        found = []
        for pattern in label_patterns:
            for m in re.finditer(pattern, report_markdown, re.IGNORECASE):
                window = report_markdown[m.end(): m.end() + 40]
                num_match = re.search(r"[-+]?[\d,]+\.?\d*", window)
                if num_match:
                    raw = num_match.group().replace(",", "")
                    try:
                        found.append(float(raw))
                    except ValueError:
                        pass
        return found

    def check(fact_key, label_patterns, unit=""):
        expected = computed_facts.get(fact_key)
        if expected is None:
            return
        found_values = find_numbers_near(label_patterns)
        if not found_values:
            return  # not mentioned verbatim; nothing to validate
        for v in found_values:
            if expected == 0:
                continue
            deviation = abs(v - expected) / abs(expected) * 100
            if deviation > tolerance_pct:
                warnings.append(
                    f"Mismatch for '{fact_key}': expected {expected}{unit}, "
                    f"found {v}{unit} in report (deviation {deviation:.1f}%)"
                )

    check("post_money_ev_mn", [r"post-money EV[^\d]{0,20}₹?"], " mn")
    check("entry_multiple_post", [r"post-money[^\n]{0,40}multiple[^\d]{0,20}"], "x")
    check("entry_multiple_pre", [r"pre-money[^\n]{0,40}multiple[^\d]{0,20}"], "x")
    check("discount_to_fair_value_pct", [r"undervalued by[^\d]{0,10}", r"discount of[^\d]{0,10}"], "%")
    check("base_case_ev_cr", [r"fair value[^\n]{0,40}₹?[\d,]+\.?\d*\s*Cr"], " Cr")
    check("implied_pe_base", [r"P/E[^\d]{0,30}"], "x")
    check("moic_base", [r"MOIC[^\d]{0,10}"], "x")

    return warnings


def assert_report_is_consistent(report_markdown, computed_facts):
    """
    Raises if validation finds mismatches. Use this to gate report delivery
    — e.g. retry generation, or surface a visible warning banner instead
    of silently shipping a report with a wrong number to the IC.
    """
    warnings = validate_report_against_facts(report_markdown, computed_facts)
    if warnings:
        raise ValueError(
            "Generated report contains figures inconsistent with computed_facts:\n"
            + "\n".join(f"  - {w}" for w in warnings)
        )