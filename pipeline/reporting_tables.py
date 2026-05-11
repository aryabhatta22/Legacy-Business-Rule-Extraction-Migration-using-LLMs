"""Aggregated result table generation for benchmarking and thesis reporting.

Produces four CSV files from the per-run result list:
  raw_results.csv         — one row per run, all metrics
  aggregated_results.csv  — grouped by (model, prompt_strategy), mean metrics
  task_results.csv        — grouped by (model, task), mean metrics
  complexity_results.csv  — grouped by (model, complexity), mean metrics
                            (skipped when no complexity labels are present)
"""

from pathlib import Path
from typing import List, Dict, Any

from experiments.pipeline_logger import get_logger


# Numeric columns that are meaningful to average across groups.
_METRIC_COLS = [
    "precision",
    "recall",
    "completeness",
    "hallucination_rate",
    "cbs",
    "structural_fidelity",
    "avg_semantic",
]


def _build_flat_rows(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert the per-run result list into flat dicts ready for a DataFrame.

    Each row corresponds to one (model, prompt, task, file) run. The
    schema_pass_rate column is a binary 1/0 so group means give a true rate.
    """
    rows = []
    for result in results:
        metrics = result.get("metrics", {})
        rows.append(
            {
                "model": result.get("model"),
                "prompt_strategy": result.get("prompt_strategy"),
                "task": result.get("task"),
                "file": result.get("file"),
                "complexity": result.get("complexity"),
                "validation_status": result.get("validation_status"),
                # Binary so that group mean equals schema pass rate for the group.
                "schema_pass_rate": 1 if result.get("validation_status") == "valid" else 0,
                "correct": metrics.get("correct", 0),
                "partial": metrics.get("partial", 0),
                "missing": metrics.get("missing", 0),
                "hallucinated": metrics.get("hallucinated", 0),
                "total_ground_truth": metrics.get("total_ground_truth", 0),
                "total_predicted": metrics.get("total_predicted", 0),
                "precision": metrics.get("precision", 0.0),
                "recall": metrics.get("recall", 0.0),
                "completeness": metrics.get("completeness", 0.0),
                "hallucination_rate": metrics.get("hallucination_rate", 0.0),
                "cbs": metrics.get("cbs", 0.0),
                # Task-specific metrics are None when not applicable so they
                # don't distort averages across tasks.
                "structural_fidelity": metrics.get("structural_fidelity"),
                "avg_semantic": metrics.get("avg_semantic"),
            }
        )
    return rows


def _aggregate(df, group_cols: List[str]):
    """Return a grouped DataFrame with mean metrics and schema pass rate count."""
    agg_dict = {col: "mean" for col in _METRIC_COLS if col in df.columns}
    agg_dict["schema_pass_rate"] = "mean"  # mean of 0/1 gives pass rate
    agg_dict["file"] = "count"             # total runs in the group

    grouped = df.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()
    grouped = grouped.rename(columns={"file": "run_count"})
    # Round all float metric columns to 4 decimal places for readability.
    for col in _METRIC_COLS + ["schema_pass_rate"]:
        if col in grouped.columns:
            grouped[col] = grouped[col].round(4)
    return grouped


def generate_all_tables(results: List[Dict[str, Any]], results_dir: Path) -> None:
    """Write all four aggregated CSV files to results_dir."""
    logger = get_logger()

    try:
        import pandas as pd
    except ImportError:
        logger.warn("pandas not available — skipping extended table generation", indent=1)
        return

    if not results:
        logger.warn("No results to aggregate — skipping table generation", indent=1)
        return

    df = pd.DataFrame(_build_flat_rows(results))

    # --- raw_results.csv: every run, all columns ---
    raw_path = results_dir / "raw_results.csv"
    df.to_csv(raw_path, index=False)
    logger.artifact_written(str(raw_path))

    # --- aggregated_results.csv: grouped by model + prompt strategy ---
    agg_path = results_dir / "aggregated_results.csv"
    _aggregate(df, ["model", "prompt_strategy"]).to_csv(agg_path, index=False)
    logger.artifact_written(str(agg_path))

    # --- task_results.csv: grouped by model + task ---
    task_path = results_dir / "task_results.csv"
    _aggregate(df, ["model", "task"]).to_csv(task_path, index=False)
    logger.artifact_written(str(task_path))

    # --- complexity_results.csv: only when complexity labels are available ---
    has_complexity = df["complexity"].notna().any()
    if has_complexity:
        complexity_path = results_dir / "complexity_results.csv"
        _aggregate(df, ["model", "complexity"]).to_csv(complexity_path, index=False)
        logger.artifact_written(str(complexity_path))
    else:
        logger.info("No complexity labels found — skipping complexity_results.csv", indent=1)
