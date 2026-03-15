"""Result storage, reporting, and analysis.

This module handles:
1. Writing detailed results to JSON
2. Generating CSV summaries with pandas
3. Computing aggregate statistics
4. Pretty-printing results
"""

import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path


class ResultReporter:
    """Handles result storage and reporting."""

    def __init__(self, results_dir: str = "experiments/results"):
        """Initialize result reporter.

        Args:
            results_dir: Directory to store results
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.json_file = self.results_dir / "results.json"
        self.csv_file = self.results_dir / "results_summary.csv"
        self.summary_file = self.results_dir / "summary.json"

        # Keep results in memory for session
        self.results: List[Dict[str, Any]] = self._load_results()

    def _load_results(self) -> List[Dict[str, Any]]:
        """Load existing results from JSON file."""
        if self.json_file.exists():
            try:
                with open(self.json_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Could not load existing results: {e}")
                return []
        return []

    def add_result(self, result: Dict[str, Any]):
        """Add a result record.

        Args:
            result: Result dictionary from EvaluationResult.to_dict()
        """
        self.results.append(result)

    def save_json(self):
        """Save all results to JSON file."""
        try:
            with open(self.json_file, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"[RESULTS] Saved {len(self.results)} results to {self.json_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save JSON results: {e}")

    def save_csv(self):
        """Save summary table to CSV using pandas if available."""
        try:
            import pandas as pd
        except ImportError:
            print("[WARN] pandas not available, skipping CSV export")
            return

        try:
            # Build summary table
            rows = []
            for result in self.results:
                row = {
                    "model": result.get("model"),
                    "prompt_strategy": result.get("prompt_strategy"),
                    "task": result.get("task"),
                    "file": result.get("file"),
                    "validation_status": result.get("validation_status"),
                    "correct": result.get("metrics", {}).get("correct", 0),
                    "missing": result.get("metrics", {}).get("missing", 0),
                    "hallucinated": result.get("metrics", {}).get("hallucinated", 0),
                    "partial": result.get("metrics", {}).get("partial", 0),
                    "timestamp": result.get("timestamp"),
                }
                rows.append(row)

            df = pd.DataFrame(rows)
            df.to_csv(self.csv_file, index=False)
            print(f"[RESULTS] Saved CSV summary to {self.csv_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save CSV: {e}")

    def generate_summary(self) -> Dict[str, Any]:
        """Generate aggregate statistics.

        Returns:
            Summary dict with totals and averages
        """
        if not self.results:
            return {}

        # Group by model and task
        summaries_by_model_task = {}

        for result in self.results:
            model = result.get("model")
            task = result.get("task")
            key = f"{model}_{task}"

            if key not in summaries_by_model_task:
                summaries_by_model_task[key] = {
                    "model": model,
                    "task": task,
                    "files": 0,
                    "correct": 0,
                    "missing": 0,
                    "hallucinated": 0,
                    "partial": 0,
                    "valid_runs": 0,
                }

            summary = summaries_by_model_task[key]
            metrics = result.get("metrics", {})

            summary["files"] += 1
            summary["correct"] += metrics.get("correct", 0)
            summary["missing"] += metrics.get("missing", 0)
            summary["hallucinated"] += metrics.get("hallucinated", 0)
            summary["partial"] += metrics.get("partial", 0)

            if result.get("validation_status") == "valid":
                summary["valid_runs"] += 1

        # Compute aggregate summary
        aggregate = {
            "total_results": len(self.results),
            "run_timestamp": datetime.utcnow().isoformat() + "Z",
            "by_model_task": list(summaries_by_model_task.values()),
        }

        # Compute global statistics
        total_correct = sum(r.get("metrics", {}).get("correct", 0) for r in self.results)
        total_missing = sum(r.get("metrics", {}).get("missing", 0) for r in self.results)
        total_hallucinated = sum(r.get("metrics", {}).get("hallucinated", 0) for r in self.results)

        total_predicted = total_correct + total_hallucinated
        total_ground_truth = total_correct + total_missing

        aggregate["global"] = {
            "total_correct": total_correct,
            "total_missing": total_missing,
            "total_hallucinated": total_hallucinated,
            "precision": round(total_correct / total_predicted, 4) if total_predicted > 0 else 0.0,
            "recall": round(total_correct / total_ground_truth, 4) if total_ground_truth > 0 else 0.0,
        }

        return aggregate

    def save_summary(self):
        """Generate and save summary JSON."""
        try:
            summary = self.generate_summary()
            with open(self.summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"[RESULTS] Saved summary to {self.summary_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save summary: {e}")

    def print_summary(self):
        """Pretty-print summary to console."""
        summary = self.generate_summary()

        print("\n" + "=" * 60)
        print("EXPERIMENT SUMMARY")
        print("=" * 60)
        print(f"Total results: {summary.get('total_results', 0)}")
        print(f"Timestamp: {summary.get('run_timestamp', 'N/A')}")

        global_stats = summary.get("global", {})
        print("\nGlobal Statistics:")
        print(f"  Correct:      {global_stats.get('total_correct', 0)}")
        print(f"  Missing:      {global_stats.get('total_missing', 0)}")
        print(f"  Hallucinated: {global_stats.get('total_hallucinated', 0)}")
        print(f"  Precision:    {global_stats.get('precision', 0.0):.4f}")
        print(f"  Recall:       {global_stats.get('recall', 0.0):.4f}")

        print("\nResults by Model & Task:")
        for item in summary.get("by_model_task", []):
            print(f"\n  {item['model']} - {item['task'].upper()}")
            print(f"    Files processed:  {item['files']}")
            print(f"    Valid runs:       {item['valid_runs']}")
            print(f"    Correct:          {item['correct']}")
            print(f"    Missing:          {item['missing']}")
            print(f"    Hallucinated:     {item['hallucinated']}")

        print("\n" + "=" * 60 + "\n")
