"""Simple business-rule evaluation utils.

Compare inferred BusinessLogicOutput-like dicts against annotated business rules.
Matching is performed primarily by overlap of source line ranges and simple
token overlap between rule statements.

Evaluation Methodology:
  1. Extract business rules from both inferred and annotated outputs
  2. Match annotated rules to inferred rules using:
     - Evidence line overlap (lines the rule is grounded in)
     - Rule statement text overlap (semantic similarity)
  3. Classify each annotated rule as:
     - CORRECT: Found with strong statement similarity (>= 0.5 token overlap)
     - PARTIAL: Found with weaker statement similarity (< 0.5 token overlap)
     - MISSING: Not found in inferred output (no evidence overlap)
  4. Classify each inferred rule not matched as:
     - HALLUCINATED: Present in inferred but not in annotated
  5. Return summary counts and detailed matches for manual review

Line-based matching (not text-based):
  Business rules are grounded in source code line numbers (evidence).
  We match rules by evidence overlap first, then validate semantic alignment
  using rule statement text. This prevents false negatives due to paraphrasing
  while ensuring inferred rules are actually grounded in the source code.

Manual review is recommended for PARTIAL matches and hallucinations.
"""
from typing import Dict, Any, List


def _lines_overlap(a: List[int], b: List[int]) -> int:
    """Return number of overlapping lines between evidence ranges.

    Evidence line numbers ground inferred rules to source code.
    We use line overlap as the primary matching metric because:
    - Line numbers are immutable and machine-checkable
    - Rules discussing the same code region have overlapping evidence
    - This prevents spurious matches based only on text similarity
    - Inferred rules must be grounded (have evidence) to be valid
    """
    try:
        a0, a1 = int(a[0]), int(a[1])
        b0, b1 = int(b[0]), int(b[1])
        start = max(a0, b0)
        end = min(a1, b1)
        return max(0, end - start + 1)
    except Exception:
        return len(set(a) & set(b))


def _token_overlap_ratio(a: str, b: str) -> float:
    """Return token-level similarity between rule statements.

    This metric validates semantic alignment without requiring exact text match:
    - Exact text matching is too strict (LLMs may paraphrase)
    - Token overlap captures semantic intent robustly
    - Threshold of 0.5 (50%) indicates meaningful similarity
    - Used as a secondary filter after line overlap matching

    Score: |intersection| / max(|tokens_a|, |tokens_b|)
    """
    at = set([t.lower() for t in a.split() if t.isalnum()])
    bt = set([t.lower() for t in b.split() if t.isalnum()])
    if not at or not bt:
        return 0.0
    inter = at & bt
    return len(inter) / max(len(at), len(bt))


def evaluate_business(inferred: Dict[str, Any], annotated: Dict[str, Any]) -> Dict[str, Any]:
    """Compare inferred and annotated business rules.

    Matching Algorithm:
    1. For each annotated rule, find the best-matching inferred rule
       based on evidence line overlap (rules grounded in same code region)
    2. If no overlap found -> MISSING (rule not detected by LLM)
    3. If overlap found:
       - Check rule statement text similarity (>= 0.5 -> CORRECT, < 0.5 -> PARTIAL)
    4. Any inferred rule not matched -> HALLUCINATED (LLM made it up)

    Two-level Matching (Line-then-Text):
    - Primary: Evidence line overlap ensures rules are about the same code
    - Secondary: Statement text overlap validates semantic alignment

    This design ensures:
    - Annotated rules are ground truth (recall-oriented evaluation)
    - Inferred rules must be line-grounded (not just text-similar)
    - Paraphrasing is allowed (text similarity >= 0.5)
    - Hallucinations are detected (rules without annotation matches)
    """
    report = {"correct": [], "partial": [], "missing": [], "hallucinated": []}

    inferred_rules = []
    for r in inferred.get("business_rules", []):
        evidence = r.get("evidence", {})
        source_lines = evidence.get("source_lines") if isinstance(evidence, dict) else []
        inferred_rules.append({"id": r.get("rule_id"), "statement": r.get("rule_statement"), "lines": source_lines, "raw": r})

    annotated_rules = []
    for r in annotated.get("rules", []):
        annotated_rules.append({"id": r.get("rule_id"), "statement": r.get("natural_language_rule") or r.get("rule_statement"), "lines": r.get("source_lines") or r.get("source_lines"), "raw": r})

    matched_inferred = set()

    for a in annotated_rules:
        best = None
        best_overlap = 0
        for idx, inf in enumerate(inferred_rules):
            overlap = _lines_overlap(a["lines"], inf["lines"]) if a["lines"] and inf["lines"] else 0
            if overlap > best_overlap:
                best_overlap = overlap
                best = (idx, inf, overlap)

        if best is None or best_overlap == 0:
            report["missing"].append(a)
        else:
            idx, inf, overlap = best
            matched_inferred.add(idx)
            score = _token_overlap_ratio(a.get("statement", ""), inf.get("statement", ""))
            if score >= 0.5:
                report["correct"].append({"annotated": a, "inferred": inf, "overlap": overlap, "text_score": score})
            else:
                report["partial"].append({"annotated": a, "inferred": inf, "overlap": overlap, "text_score": score})

    for idx, inf in enumerate(inferred_rules):
        if idx not in matched_inferred:
            report["hallucinated"].append(inf)

    summary = {k: len(v) for k, v in report.items()}
    return {"summary": summary, "details": report}
