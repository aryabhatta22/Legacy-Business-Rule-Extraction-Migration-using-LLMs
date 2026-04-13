"""Structure evaluation helpers.

Matching is intentionally simple and reproducible:
1. Normalize inferred and annotated structure records.
2. Only consider candidates with compatible types and positive line overlap.
3. Match each annotated item to at most one inferred item.
4. Use name similarity only as a tie-breaker and for correct/partial labeling.
"""

from typing import Dict, Any, List, Set
import re


STRUCTURE_TYPE_MAP = {
    "DIVISION": {"METADATA", "CONFIGURATION", "DATA"},
    "SECTION": {"FILE_DEFINITION", "STORAGE", "DECLARATION"},
    "PARAGRAPH": {
        "ENTRY_POINT",
        "INITIALIZATION",
        "PROCESSING",
        "TERMINATION",
        "DATA_DEFINITION",
        "DATA_INITIALIZATION",
        "DATA_MODIFICATION",
        "DATA_TRANSFORMATION",
        "I_O",
        "FILE_IO",
    },
    "LOOP": {"LOOP", "CONTROL_FLOW"},
    "FILE_OP": {"FILE_DEFINITION", "FILE_IO", "I_O"},
    "CONDITIONAL": {"CONTROL_FLOW"},
}


def _normalize_tokens(text: str) -> Set[str]:
    """Tokenize names using lowercase alphanumeric chunks."""
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _line_overlap(a: List[int], b: List[int]) -> int:
    """Return number of overlapping lines for ranges or explicit line lists."""
    try:
        a0, a1 = int(a[0]), int(a[1])
        b0, b1 = int(b[0]), int(b[1])
        start = max(a0, b0)
        end = min(a1, b1)
        return max(0, end - start + 1)
    except Exception:
        return len(set(a or []) & set(b or []))


def _token_overlap_ratio(a: str, b: str) -> float:
    """Return normalized token overlap for structure names."""
    at = _normalize_tokens(a)
    bt = _normalize_tokens(b)
    if not at or not bt:
        return 0.0
    return len(at & bt) / max(len(at), len(bt))


def _normalize_structure(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize structure records from either schema output or annotation JSON."""
    return {
        "id": item.get("structure_id") or item.get("id"),
        "type": (item.get("structure_type") or item.get("type") or "").upper(),
        "name": item.get("name", ""),
        "lines": item.get("line_range") or item.get("lines") or [],
        "parent_id": item.get("parent_id"),
        "raw": item,
    }


def _type_compatible(inferred_type: str, annotated_type: str) -> bool:
    """Return whether the inferred type can represent the annotated type."""
    inferred_type = (inferred_type or "").upper()
    annotated_type = (annotated_type or "").upper()
    if not inferred_type or not annotated_type:
        return False
    if inferred_type == annotated_type:
        return True
    return annotated_type in STRUCTURE_TYPE_MAP.get(inferred_type, set())


def evaluate_structure_base(
    inferred: Dict[str, Any], annotated: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare inferred structure output with annotated structure ground truth."""
    report = {
        "correct": [],
        "partial": [],
        "missing": [],
        "hallucinated": [],
    }

    inferred_structs = [
        _normalize_structure(item) for item in inferred.get("structures", [])
    ]
    annotated_structs = [
        _normalize_structure(item) for item in annotated.get("structures", [])
    ]

    matched_inferred = set()

    for annotated_item in annotated_structs:
        best_index = None
        best_candidate = None
        best_overlap = 0
        best_name_score = -1.0

        for idx, inferred_item in enumerate(inferred_structs):
            if idx in matched_inferred:
                continue
            if not _type_compatible(inferred_item["type"], annotated_item["type"]):
                continue

            overlap = _line_overlap(annotated_item["lines"], inferred_item["lines"])
            if overlap <= 0:
                continue

            name_score = _token_overlap_ratio(
                annotated_item.get("name", ""),
                inferred_item.get("name", ""),
            )
            if overlap > best_overlap or (
                overlap == best_overlap and name_score > best_name_score
            ):
                best_index = idx
                best_candidate = inferred_item
                best_overlap = overlap
                best_name_score = name_score

        if best_candidate is None:
            report["missing"].append(
                {
                    "annotated": annotated_item,
                    "inferred": None,
                    "overlap": 0,
                    "name_score": 0.0,
                    "status": "missing",
                }
            )
            continue

        matched_inferred.add(best_index)
        match_record = {
            "annotated": annotated_item,
            "inferred": best_candidate,
            "overlap": best_overlap,
            "name_score": round(best_name_score, 4),
        }
        if best_name_score >= 0.5:
            match_record["status"] = "correct"
            report["correct"].append(match_record)
        else:
            match_record["status"] = "partial"
            report["partial"].append(match_record)

    for idx, inferred_item in enumerate(inferred_structs):
        if idx not in matched_inferred:
            report["hallucinated"].append(
                {
                    "annotated": None,
                    "inferred": inferred_item,
                    "overlap": 0,
                    "name_score": 0.0,
                    "status": "hallucinated",
                }
            )

    summary = {key: len(items) for key, items in report.items()}
    return {"summary": summary, "details": report}


def evaluate_structure(inferred: Dict[str, Any], annotated: Dict[str, Any]) -> Dict[str, Any]:
    """Return structure evaluation counts plus derived metrics."""
    base_report = evaluate_structure_base(inferred, annotated)
    summary = base_report["summary"]
    inferred_structs = inferred.get("structures", [])

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

    hierarchy_links = [
        item for item in inferred_structs if item.get("parent_id") is not None
    ]
    structural_fidelity = (
        len(hierarchy_links) / len(inferred_structs) if inferred_structs else 0.0
    )

    enhanced_summary = {
        **summary,
        "total_ground_truth": total_ground_truth,
        "total_predicted": total_predicted,
        "completeness": round(completeness, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "structural_fidelity": round(structural_fidelity, 4),
    }

    return {"summary": enhanced_summary, "details": base_report["details"]}
