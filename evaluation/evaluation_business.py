"""Business-rule evaluation helpers.

Rules are matched using a hybrid score:
1. Positive evidence-line overlap is required.
2. Token Jaccard similarity on the natural-language rule text breaks ties.
3. Each inferred rule can match at most one annotated rule.
"""

from typing import Dict, Any, List, Set
import re


def _normalize_tokens(text: str) -> Set[str]:
    """Tokenize rule statements using lowercase alphanumeric chunks."""
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _lines_overlap(a: List[int], b: List[int]) -> int:
    """Return the number of overlapping evidence lines."""
    try:
        a0, a1 = int(a[0]), int(a[1])
        b0, b1 = int(b[0]), int(b[1])
        start = max(a0, b0)
        end = min(a1, b1)
        return max(0, end - start + 1)
    except Exception:
        return len(set(a or []) & set(b or []))


def _token_jaccard_similarity(a: str, b: str) -> float:
    """Return simple semantic similarity using token Jaccard."""
    at = _normalize_tokens(a)
    bt = _normalize_tokens(b)
    if not at or not bt:
        return 0.0
    return len(at & bt) / len(at | bt)


def _normalize_inferred_rule(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize rules from schema output or annotation-shaped dry-run data."""
    evidence = item.get("evidence", {})
    source_lines = []
    if isinstance(evidence, dict):
        source_lines = evidence.get("source_lines") or []

    if not source_lines:
        source_lines = item.get("source_lines") or []

    return {
        "id": item.get("rule_id"),
        "statement": item.get("rule_statement")
        or item.get("natural_language_rule")
        or "",
        "lines": source_lines,
        "raw": item,
    }


def _normalize_annotated_rule(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize annotated business-rule records."""
    return {
        "id": item.get("rule_id"),
        "statement": item.get("natural_language_rule")
        or item.get("rule_statement")
        or "",
        "lines": item.get("source_lines") or [],
        "raw": item,
    }


def evaluate_business(inferred: Dict[str, Any], annotated: Dict[str, Any]) -> Dict[str, Any]:
    """Compare inferred business rules against annotated business rules."""
    report = {"correct": [], "partial": [], "missing": [], "hallucinated": []}

    inferred_rules = [
        _normalize_inferred_rule(item)
        for item in (inferred.get("business_rules", []) or inferred.get("rules", []))
    ]
    annotated_rules = [
        _normalize_annotated_rule(item) for item in annotated.get("rules", [])
    ]

    matched_inferred = set()

    for annotated_item in annotated_rules:
        best_index = None
        best_candidate = None
        best_overlap = 0
        best_similarity = -1.0

        for idx, inferred_item in enumerate(inferred_rules):
            if idx in matched_inferred:
                continue

            overlap = _lines_overlap(annotated_item["lines"], inferred_item["lines"])
            if overlap <= 0:
                continue

            semantic_score = _token_jaccard_similarity(
                annotated_item["statement"],
                inferred_item["statement"],
            )
            if overlap > best_overlap or (
                overlap == best_overlap and semantic_score > best_similarity
            ):
                best_index = idx
                best_candidate = inferred_item
                best_overlap = overlap
                best_similarity = semantic_score

        if best_candidate is None:
            report["missing"].append(
                {
                    "annotated": annotated_item,
                    "inferred": None,
                    "overlap": 0,
                    "semantic_score": 0.0,
                    "status": "missing",
                }
            )
            continue

        matched_inferred.add(best_index)
        match_record = {
            "annotated": annotated_item,
            "inferred": best_candidate,
            "overlap": best_overlap,
            "semantic_score": round(best_similarity, 4),
        }
        if best_similarity >= 0.5:
            match_record["status"] = "correct"
            report["correct"].append(match_record)
        else:
            match_record["status"] = "partial"
            report["partial"].append(match_record)

    for idx, inferred_item in enumerate(inferred_rules):
        if idx not in matched_inferred:
            report["hallucinated"].append(
                {
                    "annotated": None,
                    "inferred": inferred_item,
                    "overlap": 0,
                    "semantic_score": 0.0,
                    "status": "hallucinated",
                }
            )

    summary = {key: len(items) for key, items in report.items()}
    total_ground_truth = summary["correct"] + summary["partial"] + summary["missing"]
    total_predicted = summary["correct"] + summary["partial"] + summary["hallucinated"]
    completeness = (
        (summary["correct"] + summary["partial"]) / total_ground_truth
        if total_ground_truth > 0
        else 0.0
    )
    hallucination_rate = (
        summary["hallucinated"] / total_predicted if total_predicted > 0 else 0.0
    )

    summary.update(
        {
            "total_ground_truth": total_ground_truth,
            "total_predicted": total_predicted,
            "completeness": round(completeness, 4),
            "hallucination_rate": round(hallucination_rate, 4),
        }
    )
    return {"summary": summary, "details": report}
