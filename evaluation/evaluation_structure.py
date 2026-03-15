"""Simple structure evaluation utils.

Compare inferred structure (StructureOutput-like) against annotated structures
found in the assets `Annotated data` JSON files. The annotated format in this
repository uses 'lines' arrays and ids; this evaluator matches by line-range
overlap and simple name token overlap.

Evaluation Methodology:
  1. Extract structures from both inferred and annotated outputs
  2. Match annotated structures to inferred structures using:
     - Line range overlap (number of overlapping lines)
     - Name token overlap (word-level similarity)
  3. Classify each annotated structure as:
     - CORRECT: Found with high name similarity (>= 0.5 token overlap)
     - PARTIAL: Found with moderate name similarity (< 0.5 token overlap)
     - MISSING: Not found in inferred output (no line overlap)
  4. Classify each inferred structure not matched as:
     - HALLUCINATED: Present in inferred but not in annotated
  5. Return summary counts and detailed matches for manual review

This approach avoids exact string matching, allowing for paraphrasing and
different naming conventions while still ensuring consistency through line-level
grounding. Manual review is recommended for PARTIAL and edge cases.
"""
from typing import Dict, Any, List


def _range_overlap(a: List[int], b: List[int]) -> int:
    """Return number of overlapping lines between two inclusive ranges.

    Each range is expected to be a two-element list [start, end]. If a list
    of multiple lines is passed, fall back to set intersection.

    Line overlap is used as a robust matching metric because:
    - Line numbers are stable and immutable
    - They ground inferred structures to source code locations
    - Overlap indicates the structures refer to the same code region
    - Matching by line overlap is more resilient than exact name matching
    """
    try:
        a0, a1 = int(a[0]), int(a[1])
        b0, b1 = int(b[0]), int(b[1])
        start = max(a0, b0)
        end = min(a1, b1)
        return max(0, end - start + 1)
    except Exception:
        # fall back: treat lists as explicit line numbers
        sa = set(a)
        sb = set(b)
        return len(sa & sb)


def _token_overlap_ratio(a: str, b: str) -> float:
    """Return token-level similarity score between two strings.

    This metric is used for name similarity matching because:
    - Exact string match is too strict (paraphrasing is expected)
    - Token overlap captures semantic similarity without requiring exact wording
    - It's robust to capitalization and minor variations
    - Threshold of 0.5 (50% overlap) indicates meaningful name similarity

    The score is computed as: |intersection| / max(|tokens_a|, |tokens_b|)
    """
    at = set([t.lower() for t in a.split() if t.isalnum()])
    bt = set([t.lower() for t in b.split() if t.isalnum()])
    if not at or not bt:
        return 0.0
    inter = at & bt
    return len(inter) / max(len(at), len(bt))


def evaluate_structure_base(inferred: Dict[str, Any], annotated: Dict[str, Any]) -> Dict[str, Any]:
    """Compare inferred StructureOutput-like dict with annotated dict.

    Returns a report dict with counts and lists of matched/missing/hallucinated.

    Matching Algorithm:
    1. For each annotated structure, find the best-matching inferred structure
       based on line range overlap
    2. If no match found -> MISSING
    3. If match found:
       - Check name token similarity (>= 0.5 -> CORRECT, < 0.5 -> PARTIAL)
    4. Any inferred structure not matched -> HALLUCINATED

    This design ensures:
    - Annotated structures are the ground truth (recall-oriented)
    - Line overlap provides robust spatial grounding
    - Name similarity allows for paraphrasing while catching real errors
    """
    report = {
        "correct": [],
        "partial": [],
        "missing": [],
        "hallucinated": [],
    }

    inferred_structs = []
    # normalize inferred structure list
    for s in inferred.get("structures", []):
        lr = s.get("line_range") or s.get("lines") or []
        inferred_structs.append({
            "id": s.get("structure_id") or s.get("id"),
            "name": s.get("name"),
            "lines": lr,
            "raw": s,
        })

    annotated_structs = []
    for s in annotated.get("structures", []):
        annotated_structs.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "lines": s.get("lines") or s.get("line_range") or [],
            "raw": s,
        })

    matched_inferred = set()

    # match annotated -> inferred
    for a in annotated_structs:
        best = None
        best_overlap = 0
        for idx, inf in enumerate(inferred_structs):
            overlap = _range_overlap(a["lines"], inf["lines"]) if a["lines"] and inf["lines"] else 0
            if overlap > best_overlap:
                best_overlap = overlap
                best = (idx, inf, overlap)

        if best is None or best_overlap == 0:
            report["missing"].append(a)
        else:
            idx, inf, overlap = best
            matched_inferred.add(idx)
            name_score = _token_overlap_ratio(a.get("name", ""), inf.get("name", ""))
            if name_score >= 0.5:
                report["correct"].append({"annotated": a, "inferred": inf, "overlap": overlap, "name_score": name_score})
            else:
                report["partial"].append({"annotated": a, "inferred": inf, "overlap": overlap, "name_score": name_score})

    # any inferred not matched are hallucinated
    for idx, inf in enumerate(inferred_structs):
        if idx not in matched_inferred:
            report["hallucinated"].append(inf)

    # totals
    report_summary = {k: len(v) for k, v in report.items()}
    return {"summary": report_summary, "details": report}


def evaluate_structure(inferred: Dict[str, Any], annotated: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced evaluator that includes:
    1. Base counts (Correct/Partial/Missing/Hallucinated)
    2. Completeness & Hallucination Rate
    3. Structural Fidelity (Hierarchy check)
    """
    # 1. Run your original logic to get the base report
    # (Assuming the original logic you provided is available as 'base_report')
    base_report = evaluate_structure_base(inferred, annotated)
    summary = base_report["summary"]
    details = base_report["details"]

    # --- 6.2 Completeness Calculation ---
    # Formula: (Correct + Partial) / Total Ground Truth
    total_gt = summary["correct"] + summary["partial"] + summary["missing"]
    completeness = (summary["correct"] + summary["partial"]) / total_gt if total_gt > 0 else 0

    # --- 6.3 Hallucination Rate Calculation ---
    # Formula: Hallucinated / Total Generated
    total_gen = summary["correct"] + summary["partial"] + summary["hallucinated"]
    hallucination_rate = summary["hallucinated"] / total_gen if total_gen > 0 else 0

    # --- 6.4 Structural Fidelity ---
    # We check if 'parent_id' is used correctly to link Paragraphs to Sections/Divisions
    inferred_structs = inferred.get("structures", [])
    hierarchy_links = [s for s in inferred_structs if s.get("parent_id") is not None]

    # Fidelity is the ratio of items correctly placed in a hierarchy
    structural_fidelity = len(hierarchy_links) / len(inferred_structs) if inferred_structs else 0

    # Update Summary with new metrics
    enhanced_summary = {
        **summary,
        "completeness": round(completeness, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "structural_fidelity": round(structural_fidelity, 4),
        "total_gt": total_gt,
        "total_generated": total_gen
    }

    return {"summary": enhanced_summary, "details": details}
