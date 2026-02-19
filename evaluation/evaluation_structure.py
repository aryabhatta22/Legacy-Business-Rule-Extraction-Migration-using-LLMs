"""Simple structure evaluation utils.

Compare inferred structure (StructureOutput-like) against annotated structures
found in the assets `Annotated data` JSON files. The annotated format in this
repository uses 'lines' arrays and ids; this evaluator matches by line-range
overlap and simple name token overlap.
"""
from typing import Dict, Any, List


def _range_overlap(a: List[int], b: List[int]) -> int:
    """Return number of overlapping lines between two inclusive ranges.

    Each range is expected to be a two-element list [start, end]. If a list
    of multiple lines is passed, fall back to set intersection.
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
    at = set([t.lower() for t in a.split() if t.isalnum()])
    bt = set([t.lower() for t in b.split() if t.isalnum()])
    if not at or not bt:
        return 0.0
    inter = at & bt
    return len(inter) / max(len(at), len(bt))


def evaluate_structure(inferred: Dict[str, Any], annotated: Dict[str, Any]) -> Dict[str, Any]:
    """Compare inferred StructureOutput-like dict with annotated dict.

    Returns a report dict with counts and lists of matched/missing/hallucinated.
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
