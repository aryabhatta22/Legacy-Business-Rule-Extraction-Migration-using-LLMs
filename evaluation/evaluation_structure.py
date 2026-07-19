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

# Annotated types that correspond to root-level (DIVISION) structures.
# These legitimately have no parent, so a null parent_id is correct for them.
_DIVISION_ANNOTATED_TYPES = {"METADATA", "CONFIGURATION", "DATA"}


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


def _line_iou(a: List[int], b: List[int]) -> float:
    """Intersection-over-union of two [start, end] line ranges.

    Measures how precisely the model located the item, independent of the
    binary overlap gate. Uses the same [first, second] range convention as
    _line_overlap, with the same set-based fallback for explicit line lists.
    """
    try:
        a0, a1 = int(a[0]), int(a[1])
        b0, b1 = int(b[0]), int(b[1])
        inter = max(0, min(a1, b1) - max(a0, b0) + 1)
        union = max(a1, b1) - min(a0, b0) + 1
        return inter / union if union > 0 else 0.0
    except Exception:
        sa, sb = set(a or []), set(b or [])
        return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


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


def _compute_structural_fidelity(correct_matches: List[Dict[str, Any]]) -> float:
    """Measure how well the model preserves the COBOL parent-child hierarchy.

    For each correctly matched structure:
    - If the annotated type is a root (DIVISION-level), a null parent_id is correct.
    - Otherwise, the inferred parent_id must point to another correctly matched structure,
      meaning the parent was also correctly identified.

    Returns correct_with_valid_parent / total_correct.
    """
    if not correct_matches:
        return 0.0

    # Collect the inferred IDs of all correctly matched structures so we can
    # check whether a given parent_id resolves to a correct match.
    correct_inferred_ids = {
        m["inferred"]["id"]
        for m in correct_matches
        if m.get("inferred") and m["inferred"].get("id")
    }

    valid_parent_count = 0
    for match in correct_matches:
        inferred = match.get("inferred") or {}
        annotated = match.get("annotated") or {}
        parent_id = inferred.get("parent_id")

        if parent_id is None:
            # Root structures (divisions) should have no parent — this is correct.
            if annotated.get("type") in _DIVISION_ANNOTATED_TYPES:
                valid_parent_count += 1
        else:
            # Non-root structures must reference a parent that was itself correct.
            if parent_id in correct_inferred_ids:
                valid_parent_count += 1

    return round(valid_parent_count / len(correct_matches), 4)


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
            "line_iou": round(
                _line_iou(annotated_item["lines"], best_candidate["lines"]), 4
            ),
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

    # Structural fidelity: proportion of correct matches whose parent relationship
    # is also correct. Uses the fixed _compute_structural_fidelity helper — the old
    # implementation counted any inferred structure with a parent_id set, which
    # measured nothing about correctness and always returned 0.0 in dry-run mode.
    structural_fidelity = _compute_structural_fidelity(base_report["details"]["correct"])

    # Mean line-range IoU over matched pairs — how precisely matched structures
    # were located, complementing the binary overlap gate.
    matched = base_report["details"]["correct"] + base_report["details"]["partial"]
    iou_values = [m.get("line_iou", 0.0) for m in matched]
    avg_line_iou = round(sum(iou_values) / len(iou_values), 4) if iou_values else 0.0

    enhanced_summary = {
        **summary,
        "total_ground_truth": total_ground_truth,
        "total_predicted": total_predicted,
        "completeness": round(completeness, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "structural_fidelity": structural_fidelity,
        "avg_line_iou": avg_line_iou,
    }

    return {"summary": enhanced_summary, "details": base_report["details"]}
