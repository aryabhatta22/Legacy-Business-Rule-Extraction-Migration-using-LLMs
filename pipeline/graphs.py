"""Benchmark visualization module.

Generates seven reproducible charts from per-run result data and saves them
to experiments/results/graphs/. All charts use matplotlib only — no seaborn
or other styling libraries — to keep the dependency footprint minimal.

Charts produced:
  cbs_ranking.png               — CBS per (model + prompt) group, sorted
  metric_comparison.png         — P / R / C / H per model
  hallucination_vs_cbs.png      — scatter: hallucination rate vs CBS
  prompt_strategy_comparison.png — mean CBS per prompt strategy, split by task
  cbs_by_complexity.png         — mean CBS per complexity level × model
  schema_pass_rate.png          — schema pass rate per model
  structural_fidelity.png       — structural fidelity per model (structure only)
"""

from pathlib import Path
from typing import List, Dict, Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend so charts save without a display
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

from experiments.pipeline_logger import get_logger

# Resolution for all saved figures.
_DPI = 150


def _build_df(results: List[Dict[str, Any]]):
    """Convert results list to a pandas DataFrame. Returns None on failure."""
    try:
        import pandas as pd
    except ImportError:
        return None

    rows = []
    for r in results:
        m = r.get("metrics", {})
        rows.append(
            {
                "model": r.get("model", "unknown"),
                "prompt_strategy": r.get("prompt_strategy", "unknown"),
                "task": r.get("task", "unknown"),
                "file": r.get("file", "unknown"),
                "complexity": r.get("complexity"),
                "schema_pass": 1 if r.get("validation_status") == "valid" else 0,
                "precision": m.get("precision", 0.0),
                "recall": m.get("recall", 0.0),
                "completeness": m.get("completeness", 0.0),
                "hallucination_rate": m.get("hallucination_rate", 0.0),
                "cbs": m.get("cbs", 0.0),
                "structural_fidelity": m.get("structural_fidelity"),
                "avg_semantic": m.get("avg_semantic"),
            }
        )
    return __import__("pandas").DataFrame(rows)


def _colors_for(labels):
    """Return one distinct colour per unique label."""
    palette = cm.get_cmap("tab10")
    unique = list(dict.fromkeys(labels))  # preserve order, deduplicate
    color_map = {label: palette(i / max(len(unique), 1)) for i, label in enumerate(unique)}
    return [color_map[label] for label in labels], color_map


def _save(fig, path: Path, logger) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    logger.artifact_written(str(path))


# ---------------------------------------------------------------------------
# Chart 1 — CBS Ranking
# ---------------------------------------------------------------------------

def _chart_cbs_ranking(df, out_dir: Path, logger) -> None:
    """Horizontal bar chart: mean CBS per (model, prompt_strategy) group."""
    grouped = (
        df.groupby(["model", "prompt_strategy"])["cbs"]
        .mean()
        .reset_index()
        .sort_values("cbs", ascending=True)
    )
    if grouped.empty:
        return

    labels = [f"{r.model}\n{r.prompt_strategy}" for r in grouped.itertuples()]
    colors, _ = _colors_for([r.model for r in grouped.itertuples()])

    fig, ax = plt.subplots(figsize=(10, max(4, len(labels) * 0.45)))
    bars = ax.barh(labels, grouped["cbs"], color=colors)
    ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
    ax.set_xlabel("Composite Benchmark Score (CBS)")
    ax.set_title("CBS Ranking by Model × Prompt Strategy")
    ax.set_xlim(0, 1.05)
    _save(fig, out_dir / "cbs_ranking.png", logger)


# ---------------------------------------------------------------------------
# Chart 2 — Metric Comparison per Model
# ---------------------------------------------------------------------------

def _chart_metric_comparison(df, out_dir: Path, logger) -> None:
    """Grouped bar chart: precision, recall, completeness, hallucination per model."""
    metrics = ["precision", "recall", "completeness", "hallucination_rate"]
    grouped = df.groupby("model")[metrics].mean().reset_index()
    if grouped.empty:
        return

    models = grouped["model"].tolist()
    x = np.arange(len(models))
    width = 0.2
    fig, ax = plt.subplots(figsize=(max(6, len(models) * 2), 5))

    for i, metric in enumerate(metrics):
        offset = (i - len(metrics) / 2 + 0.5) * width
        ax.bar(x + offset, grouped[metric], width, label=metric)

    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=15, ha="right", fontsize=8)
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.1)
    ax.set_title("Metric Comparison by Model")
    ax.legend(fontsize=8)
    _save(fig, out_dir / "metric_comparison.png", logger)


# ---------------------------------------------------------------------------
# Chart 3 — Hallucination vs CBS Scatter
# ---------------------------------------------------------------------------

def _chart_hallucination_vs_cbs(df, out_dir: Path, logger) -> None:
    """Scatter: x = hallucination_rate, y = CBS, coloured by model."""
    if df.empty:
        return

    models = df["model"].unique().tolist()
    _, color_map = _colors_for(models)

    fig, ax = plt.subplots(figsize=(8, 6))
    for model, group in df.groupby("model"):
        ax.scatter(
            group["hallucination_rate"],
            group["cbs"],
            label=model,
            color=color_map.get(model),
            alpha=0.7,
            s=60,
        )

    ax.set_xlabel("Hallucination Rate")
    ax.set_ylabel("Composite Benchmark Score (CBS)")
    ax.set_title("Hallucination Rate vs CBS")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=8, loc="upper right")
    _save(fig, out_dir / "hallucination_vs_cbs.png", logger)


# ---------------------------------------------------------------------------
# Chart 4 — Prompt Strategy Comparison
# ---------------------------------------------------------------------------

def _chart_prompt_strategy_comparison(df, out_dir: Path, logger) -> None:
    """Bar chart: mean CBS per prompt strategy, split by task (structure / business)."""
    tasks = df["task"].unique().tolist()
    strategies = df["prompt_strategy"].unique().tolist()
    if not strategies:
        return

    x = np.arange(len(strategies))
    width = 0.35
    fig, ax = plt.subplots(figsize=(max(7, len(strategies) * 1.5), 5))

    for i, task in enumerate(tasks):
        task_df = df[df["task"] == task]
        means = task_df.groupby("prompt_strategy")["cbs"].mean().reindex(strategies, fill_value=0)
        offset = (i - len(tasks) / 2 + 0.5) * width
        ax.bar(x + offset, means.values, width, label=task)

    ax.set_xticks(x)
    ax.set_xticklabels(strategies, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Mean CBS")
    ax.set_ylim(0, 1.1)
    ax.set_title("Prompt Strategy Comparison by Task")
    ax.legend(fontsize=8)
    _save(fig, out_dir / "prompt_strategy_comparison.png", logger)


# ---------------------------------------------------------------------------
# Chart 5 — CBS by Complexity
# ---------------------------------------------------------------------------

def _chart_cbs_by_complexity(df, out_dir: Path, logger) -> None:
    """Bar chart: mean CBS per complexity level × model. Skipped if no labels."""
    if df["complexity"].isna().all():
        logger.info("No complexity labels — skipping cbs_by_complexity.png", indent=1)
        return

    complexity_df = df.dropna(subset=["complexity"])
    grouped = complexity_df.groupby(["complexity", "model"])["cbs"].mean().reset_index()
    complexities = sorted(grouped["complexity"].unique())
    models = sorted(grouped["model"].unique())
    _, color_map = _colors_for(models)

    x = np.arange(len(complexities))
    width = 0.8 / max(len(models), 1)
    fig, ax = plt.subplots(figsize=(max(6, len(complexities) * 2), 5))

    for i, model in enumerate(models):
        model_data = grouped[grouped["model"] == model]
        means = (
            model_data.set_index("complexity")["cbs"]
            .reindex(complexities, fill_value=0)
        )
        offset = (i - len(models) / 2 + 0.5) * width
        ax.bar(x + offset, means.values, width, label=model, color=color_map.get(model))

    ax.set_xticks(x)
    ax.set_xticklabels(complexities)
    ax.set_ylabel("Mean CBS")
    ax.set_ylim(0, 1.1)
    ax.set_title("CBS by Complexity Level × Model")
    ax.legend(fontsize=8)
    _save(fig, out_dir / "cbs_by_complexity.png", logger)


# ---------------------------------------------------------------------------
# Chart 6 — Schema Pass Rate per Model
# ---------------------------------------------------------------------------

def _chart_schema_pass_rate(df, out_dir: Path, logger) -> None:
    """Bar chart: schema pass rate (valid / total) per model."""
    grouped = df.groupby("model")["schema_pass"].mean().reset_index()
    grouped = grouped.sort_values("schema_pass", ascending=False)
    if grouped.empty:
        return

    colors, _ = _colors_for(grouped["model"].tolist())
    fig, ax = plt.subplots(figsize=(max(5, len(grouped) * 1.2), 4))
    bars = ax.bar(grouped["model"], grouped["schema_pass"], color=colors)
    ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=9)
    ax.set_ylabel("Schema Pass Rate")
    ax.set_ylim(0, 1.15)
    ax.set_title("Schema Validation Pass Rate by Model")
    ax.tick_params(axis="x", rotation=15)
    _save(fig, out_dir / "schema_pass_rate.png", logger)


# ---------------------------------------------------------------------------
# Chart 7 — Structural Fidelity per Model (structure task only)
# ---------------------------------------------------------------------------

def _chart_structural_fidelity(df, out_dir: Path, logger) -> None:
    """Bar chart: mean structural_fidelity per model, structure task runs only."""
    struct_df = df[df["task"] == "structure"].dropna(subset=["structural_fidelity"])
    if struct_df.empty:
        logger.info("No structural fidelity data — skipping structural_fidelity.png", indent=1)
        return

    grouped = struct_df.groupby("model")["structural_fidelity"].mean().reset_index()
    grouped = grouped.sort_values("structural_fidelity", ascending=False)
    colors, _ = _colors_for(grouped["model"].tolist())

    fig, ax = plt.subplots(figsize=(max(5, len(grouped) * 1.2), 4))
    bars = ax.bar(grouped["model"], grouped["structural_fidelity"], color=colors)
    ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=9)
    ax.set_ylabel("Structural Fidelity")
    ax.set_ylim(0, 1.15)
    ax.set_title("Structural Fidelity by Model (Structure Task)")
    ax.tick_params(axis="x", rotation=15)
    _save(fig, out_dir / "structural_fidelity.png", logger)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_all_graphs(results: List[Dict[str, Any]], graphs_dir: Path) -> None:
    """Generate all seven benchmark charts and save to graphs_dir."""
    logger = get_logger()

    df = _build_df(results)
    if df is None:
        logger.warn("pandas not available — skipping graph generation", indent=1)
        return
    if df.empty:
        logger.warn("No results — skipping graph generation", indent=1)
        return

    _chart_cbs_ranking(df, graphs_dir, logger)
    _chart_metric_comparison(df, graphs_dir, logger)
    _chart_hallucination_vs_cbs(df, graphs_dir, logger)
    _chart_prompt_strategy_comparison(df, graphs_dir, logger)
    _chart_cbs_by_complexity(df, graphs_dir, logger)
    _chart_schema_pass_rate(df, graphs_dir, logger)
    _chart_structural_fidelity(df, graphs_dir, logger)
