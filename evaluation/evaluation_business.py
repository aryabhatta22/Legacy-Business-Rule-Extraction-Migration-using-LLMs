"""Simple business-rule evaluation utils.

Compare inferred BusinessLogicOutput-like dicts against annotated business rules.
Matching is performed primarily by overlap of source line ranges and simple
token overlap between rule statements.
"""
from typing import Dict, Any, List


def _lines_overlap(a: List[int], b: List[int]) -> int:
    try:
        a0, a1 = int(a[0]), int(a[1])
        b0, b1 = int(b[0]), int(b[1])
        start = max(a0, b0)
        end = min(a1, b1)
        return max(0, end - start + 1)
    except Exception:
        return len(set(a) & set(b))


def _token_overlap_ratio(a: str, b: str) -> float:
    at = set([t.lower() for t in a.split() if t.isalnum()])
    bt = set([t.lower() for t in b.split() if t.isalnum()])
    if not at or not bt:
        return 0.0
    inter = at & bt
    return len(inter) / max(len(at), len(bt))


def evaluate_business(inferred: Dict[str, Any], annotated: Dict[str, Any]) -> Dict[str, Any]:
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
