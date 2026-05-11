"""Benchmark analysis summary generation.

Reads the per-run result list and writes two files to experiments/results/:

  analysis_summary.json — machine-readable structured findings
  analysis_summary.txt  — human-readable text for thesis appendix

Findings reported:
  best_overall_cbs          — highest CBS single run
  best_structural_fidelity  — highest structural_fidelity (structure task)
  best_schema_pass_rate     — model with highest schema pass rate
  best_semantic_faithfulness — highest avg_semantic (business task)
  lowest_hallucination      — run with lowest hallucination_rate
  cbs_by_complexity         — mean CBS per complexity level
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from experiments.pipeline_logger import get_logger


def _safe_get(result: Dict[str, Any], *keys, default=None):
    """Drill into nested dicts safely."""
    obj = result
    for key in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(key, default)
    return obj


def _best_by(results: List[Dict[str, Any]], metric_key: str, task_filter: Optional[str] = None):
    """Return the result dict with the highest value of metrics[metric_key].

    Filters to task_filter when provided. Returns None when no valid rows exist.
    """
    candidates = [
        r for r in results
        if (task_filter is None or r.get("task") == task_filter)
        and _safe_get(r, "metrics", metric_key) is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda r: _safe_get(r, "metrics", metric_key, default=0.0))


def _best_schema_pass_rate(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute schema pass rate per model and return the best-performing model."""
    model_counts: Dict[str, Dict[str, int]] = {}
    for r in results:
        model = r.get("model", "unknown")
        if model not in model_counts:
            model_counts[model] = {"valid": 0, "total": 0}
        model_counts[model]["total"] += 1
        if r.get("validation_status") == "valid":
            model_counts[model]["valid"] += 1

    if not model_counts:
        return {}

    best_model = max(
        model_counts,
        key=lambda m: model_counts[m]["valid"] / max(model_counts[m]["total"], 1),
    )
    counts = model_counts[best_model]
    rate = round(counts["valid"] / max(counts["total"], 1), 4)
    return {
        "model": best_model,
        "valid_runs": counts["valid"],
        "total_runs": counts["total"],
        "schema_pass_rate": rate,
    }


def _cbs_by_complexity(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return mean CBS per complexity level. Empty dict when no labels exist."""
    buckets: Dict[str, List[float]] = {}
    for r in results:
        level = r.get("complexity")
        cbs = _safe_get(r, "metrics", "cbs")
        if level and cbs is not None:
            buckets.setdefault(level, []).append(float(cbs))

    return {
        level: round(sum(scores) / len(scores), 4)
        for level, scores in sorted(buckets.items())
    }


def _result_summary(result: Optional[Dict[str, Any]], *metric_keys: str) -> Dict[str, Any]:
    """Extract identifying fields and requested metric keys from a result dict."""
    if result is None:
        return {}
    row = {
        "model": result.get("model"),
        "prompt_strategy": result.get("prompt_strategy"),
        "task": result.get("task"),
        "file": result.get("file"),
        "complexity": result.get("complexity"),
    }
    metrics = result.get("metrics", {})
    for key in metric_keys:
        row[key] = metrics.get(key)
    return row


def _as_text(summary: Dict[str, Any]) -> str:
    """Format the analysis summary dict as a readable text report."""
    lines = [
        "=== COBOL LLM Benchmark — Analysis Summary ===",
        "",
    ]

    def _row(label: str, d: Dict[str, Any], *keys: str) -> str:
        parts = [f"{k}={d.get(k)}" for k in keys if d.get(k) is not None]
        return f"  {label}: {', '.join(parts)}" if parts else f"  {label}: n/a"

    best_cbs = summary.get("best_overall_cbs", {})
    lines.append("Best Overall CBS")
    lines.append(_row("", best_cbs, "model", "prompt_strategy", "task", "file", "cbs"))

    best_sf = summary.get("best_structural_fidelity", {})
    lines.append("\nBest Structural Fidelity")
    lines.append(_row("", best_sf, "model", "prompt_strategy", "structural_fidelity"))

    best_spr = summary.get("best_schema_pass_rate", {})
    lines.append("\nBest Schema Pass Rate")
    lines.append(_row("", best_spr, "model", "valid_runs", "total_runs", "schema_pass_rate"))

    best_sem = summary.get("best_semantic_faithfulness", {})
    lines.append("\nBest Semantic Faithfulness (Business Task)")
    lines.append(_row("", best_sem, "model", "prompt_strategy", "avg_semantic"))

    low_hall = summary.get("lowest_hallucination", {})
    lines.append("\nLowest Hallucination Rate")
    lines.append(_row("", low_hall, "model", "prompt_strategy", "task", "hallucination_rate"))

    cbs_complexity = summary.get("cbs_by_complexity", {})
    if cbs_complexity:
        lines.append("\nMean CBS by Complexity")
        for level, score in cbs_complexity.items():
            lines.append(f"  {level}: {score}")

    lines.append("")
    return "\n".join(lines)


def generate_analysis(results: List[Dict[str, Any]], results_dir: Path) -> None:
    """Compute benchmark analysis findings and write JSON + text summaries."""
    logger = get_logger()

    if not results:
        logger.warn("No results — skipping analysis generation", indent=1)
        return

    best_cbs_run = _best_by(results, "cbs")
    best_sf_run = _best_by(results, "structural_fidelity", task_filter="structure")
    best_sem_run = _best_by(results, "avg_semantic", task_filter="business")

    # Lowest hallucination: exclude runs where nothing was predicted (rate == 0 trivially).
    non_trivial = [
        r for r in results
        if _safe_get(r, "metrics", "total_predicted", default=0) > 0
    ]
    low_hall_run = (
        min(non_trivial, key=lambda r: _safe_get(r, "metrics", "hallucination_rate", default=1.0))
        if non_trivial else None
    )

    summary = {
        "best_overall_cbs": _result_summary(best_cbs_run, "cbs"),
        "best_structural_fidelity": _result_summary(best_sf_run, "structural_fidelity"),
        "best_schema_pass_rate": _best_schema_pass_rate(results),
        "best_semantic_faithfulness": _result_summary(best_sem_run, "avg_semantic"),
        "lowest_hallucination": _result_summary(low_hall_run, "hallucination_rate"),
        "cbs_by_complexity": _cbs_by_complexity(results),
    }

    json_path = results_dir / "analysis_summary.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    logger.artifact_written(str(json_path))

    txt_path = results_dir / "analysis_summary.txt"
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(_as_text(summary))
    logger.artifact_written(str(txt_path))
