"""Result storage, reporting, and analysis."""

import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

from experiments.pipeline_logger import get_logger


class ResultReporter:
    """Handles deterministic result storage for a single pipeline run."""

    def __init__(self, results_dir: str = "experiments/results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.json_file = self.results_dir / "results.json"
        self.csv_file = self.results_dir / "results_summary.csv"
        self.summary_file = self.results_dir / "summary.json"

        # Start each run from a clean in-memory result set so artifacts are
        # reproducible and never mix multiple experiments together.
        self.results: List[Dict[str, Any]] = []

    def add_result(self, result: Dict[str, Any]):
        """Add a per-run result dictionary."""
        self.results.append(result)

    def save_json(self):
        """Write detailed results to JSON."""
        logger = get_logger()
        with open(self.json_file, "w", encoding="utf-8") as fh:
            json.dump(self.results, fh, indent=2, default=str)
        logger.artifact_written(str(self.json_file))

    def save_csv(self):
        """Write per-run summary rows to CSV with all benchmark metrics."""
        logger = get_logger()
        try:
            import pandas as pd
        except ImportError:
            logger.warn("pandas not available, skipping CSV export", indent=1)
            return

        rows = []
        for result in self.results:
            metrics = result.get("metrics", {})
            # schema_pass_rate is 1 for a valid run, 0 otherwise. Aggregate
            # rates are computed from these binary values in reporting_tables.py.
            schema_pass = 1 if result.get("validation_status") == "valid" else 0
            rows.append(
                {
                    "model": result.get("model"),
                    "prompt_strategy": result.get("prompt_strategy"),
                    "task": result.get("task"),
                    "file": result.get("file"),
                    "complexity": result.get("complexity"),
                    "validation_status": result.get("validation_status"),
                    "schema_pass_rate": schema_pass,
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
                    "structural_fidelity": metrics.get("structural_fidelity"),
                    "avg_semantic": metrics.get("avg_semantic"),
                    "timestamp": result.get("timestamp"),
                }
            )

        pd.DataFrame(rows).to_csv(self.csv_file, index=False)
        logger.artifact_written(str(self.csv_file))

    def generate_summary(self) -> Dict[str, Any]:
        """Build aggregate statistics for backward-compatible summary output."""
        if not self.results:
            return {
                "total_results": 0,
                "run_timestamp": datetime.utcnow().isoformat() + "Z",
                "by_model_task": [],
                "global": {},
            }

        grouped: Dict[str, Dict[str, Any]] = {}
        for result in self.results:
            model = result.get("model")
            task = result.get("task")
            key = f"{model}_{task}"
            metrics = result.get("metrics", {})

            if key not in grouped:
                grouped[key] = {
                    "model": model,
                    "task": task,
                    "files": 0,
                    "valid_runs": 0,
                    "correct": 0,
                    "partial": 0,
                    "missing": 0,
                    "hallucinated": 0,
                }

            grouped[key]["files"] += 1
            grouped[key]["correct"] += metrics.get("correct", 0)
            grouped[key]["partial"] += metrics.get("partial", 0)
            grouped[key]["missing"] += metrics.get("missing", 0)
            grouped[key]["hallucinated"] += metrics.get("hallucinated", 0)
            if result.get("validation_status") == "valid":
                grouped[key]["valid_runs"] += 1

        total_correct = sum(r.get("metrics", {}).get("correct", 0) for r in self.results)
        total_partial = sum(r.get("metrics", {}).get("partial", 0) for r in self.results)
        total_missing = sum(r.get("metrics", {}).get("missing", 0) for r in self.results)
        total_hallucinated = sum(
            r.get("metrics", {}).get("hallucinated", 0) for r in self.results
        )

        total_ground_truth = total_correct + total_partial + total_missing
        total_predicted = total_correct + total_partial + total_hallucinated

        precision = round(total_correct / total_predicted, 4) if total_predicted > 0 else 0.0
        recall = round(total_correct / total_ground_truth, 4) if total_ground_truth > 0 else 0.0
        completeness = (
            round((total_correct + total_partial) / total_ground_truth, 4)
            if total_ground_truth > 0 else 0.0
        )
        hallucination_rate = (
            round(total_hallucinated / total_predicted, 4) if total_predicted > 0 else 0.0
        )
        cbs = round(
            0.40 * recall
            + 0.30 * precision
            + 0.20 * (1.0 - hallucination_rate)
            + 0.10 * completeness,
            4,
        )

        return {
            "total_results": len(self.results),
            "run_timestamp": datetime.utcnow().isoformat() + "Z",
            "by_model_task": list(grouped.values()),
            "global": {
                "total_correct": total_correct,
                "total_partial": total_partial,
                "total_missing": total_missing,
                "total_hallucinated": total_hallucinated,
                "total_ground_truth": total_ground_truth,
                "total_predicted": total_predicted,
                "precision": precision,
                "recall": recall,
                "completeness": completeness,
                "hallucination_rate": hallucination_rate,
                "cbs": cbs,
            },
        }

    def save_summary(self):
        """Write aggregate statistics to summary.json."""
        logger = get_logger()
        with open(self.summary_file, "w", encoding="utf-8") as fh:
            json.dump(self.generate_summary(), fh, indent=2, default=str)
        logger.artifact_written(str(self.summary_file))

    def generate_extended_outputs(self):
        """Generate aggregated tables, graphs, and analysis summary.

        Called once after all runs complete. Each module is imported here so the
        pipeline still runs correctly even if a module has an import error — the
        logger will report the problem without stopping the main results from saving.
        """
        logger = get_logger()

        try:
            from pipeline.reporting_tables import generate_all_tables
            generate_all_tables(self.results, self.results_dir)
        except Exception as exc:
            logger.warn(f"reporting_tables failed: {exc}", indent=1)

        try:
            from pipeline.graphs import generate_all_graphs
            graphs_dir = self.results_dir / "graphs"
            graphs_dir.mkdir(parents=True, exist_ok=True)
            generate_all_graphs(self.results, graphs_dir)
        except Exception as exc:
            logger.warn(f"graphs failed: {exc}", indent=1)

        try:
            from pipeline.analysis import generate_analysis
            generate_analysis(self.results, self.results_dir)
        except Exception as exc:
            logger.warn(f"analysis failed: {exc}", indent=1)

    def print_summary(self):
        """Log a concise end-of-run summary."""
        logger = get_logger()
        summary = self.generate_summary()
        logger.info(
            f"Run summary: total_results={summary.get('total_results', 0)}",
            indent=0,
        )
        global_stats = summary.get("global", {})
        if global_stats:
            logger.info(
                "Global metrics: "
                f"precision={global_stats.get('precision', 0.0)} "
                f"recall={global_stats.get('recall', 0.0)} "
                f"completeness={global_stats.get('completeness', 0.0)} "
                f"hallucination_rate={global_stats.get('hallucination_rate', 0.0)} "
                f"cbs={global_stats.get('cbs', 0.0)}",
                indent=0,
            )
