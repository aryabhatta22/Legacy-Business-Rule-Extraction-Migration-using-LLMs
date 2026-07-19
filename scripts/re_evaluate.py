"""Re-evaluate saved LLM outputs without calling any LLM (T2 / P2).

Reads an existing results.json (each record already holds `llm_output` and
`ground_truth`), re-runs the evaluators on every record, and rewrites the
standard artifacts (results.json, results_summary.csv, summary.json, aggregated
tables, graphs, analysis) via the same ResultReporter used by main.py.

Never calls an LLM and never touches experiments/log.jsonl.

Usage (from the repo root):
    uv run python scripts/re_evaluate.py
    uv run python scripts/re_evaluate.py --input experiments/archive/results_live_openai_vscbex01.json
    uv run python scripts/re_evaluate.py --results-dir experiments/results_reevaluated
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from evaluation.evaluation_business import evaluate_business
from evaluation.evaluation_structure import evaluate_structure
from experiments.pipeline_logger import get_logger, init_logger
from pipeline.evaluation import build_evaluation_result
from pipeline.result_reporter import ResultReporter


def _empty_evaluation_report():
    """Same empty-report shape main.py uses when a record cannot be evaluated."""
    return {
        "summary": {
            "correct": 0,
            "partial": 0,
            "missing": 0,
            "hallucinated": 0,
            "total_ground_truth": 0,
            "total_predicted": 0,
            "completeness": 0.0,
            "hallucination_rate": 0.0,
        },
        "details": {
            "correct": [],
            "partial": [],
            "missing": [],
            "hallucinated": [],
        },
    }


def re_evaluate_record(record: dict) -> dict:
    """Re-run the task's evaluator on one saved record and rebuild its metrics.

    Mirrors main.py's per-run behavior: a missing/failed llm_output is evaluated
    as an empty prediction — it must never fall back to ground truth.
    """
    task = record.get("task")
    llm_output = record.get("llm_output") or {}
    ground_truth = record.get("ground_truth") or {}

    if not ground_truth:
        eval_report = _empty_evaluation_report()
    elif task == "structure":
        eval_report = evaluate_structure(llm_output, ground_truth)
    elif task == "business":
        eval_report = evaluate_business(llm_output, ground_truth)
    else:
        raise ValueError(f"Unknown task {task!r} in record: {record.get('file')}")

    result = build_evaluation_result(
        model=record.get("model"),
        prompt_strategy=record.get("prompt_strategy"),
        task=task,
        file=record.get("file"),
        validation_status=record.get("validation_status"),
        llm_output=record.get("llm_output"),
        ground_truth=record.get("ground_truth"),
        evaluation_report=eval_report,
        complexity=record.get("complexity"),
        raw_response=record.get("raw_response"),
        error_message=record.get("error_message"),
    )
    result_dict = result.to_dict()

    # Keep the original run timestamp so records stay traceable to the run that
    # produced the LLM output; the re-evaluation moment is stored separately.
    if record.get("timestamp"):
        result_dict["timestamp"] = record["timestamp"]
    result_dict["re_evaluated_at"] = datetime.utcnow().isoformat() + "Z"
    return result_dict


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--input",
        default="experiments/results/results.json",
        help="results.json to re-evaluate (default: experiments/results/results.json)",
    )
    parser.add_argument(
        "--results-dir",
        default="experiments/results",
        help="directory to write regenerated artifacts into (default: experiments/results)",
    )
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    # Separate log file so this script never clobbers the last pipeline run_log.txt.
    init_logger("experiments/re_evaluate_log.txt")
    logger = get_logger()

    with open(args.input, "r", encoding="utf-8") as fh:
        records = json.load(fh)
    logger.info(f"Loaded {len(records)} records from {args.input}", indent=0)

    structure_count = sum(1 for r in records if r.get("task") == "structure")
    if structure_count:
        logger.warn(
            f"{structure_count} structure-task records re-evaluated with the CURRENT "
            "evaluator — until T1/P1 (missing annotated names) is fixed, their "
            "'correct' counts stay 0 and must be treated as provisional.",
            indent=0,
        )

    reporter = ResultReporter(results_dir=args.results_dir)
    for record in records:
        reporter.add_result(re_evaluate_record(record))

    reporter.save_json()
    reporter.save_csv()
    reporter.save_summary()
    reporter.generate_extended_outputs()
    reporter.print_summary()
    logger.info("Re-evaluation complete. experiments/log.jsonl was not modified.", indent=0)


if __name__ == "__main__":
    main()
