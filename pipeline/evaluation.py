"""Detailed evaluation result tracking and reporting.

This module handles:
1. Detailed evaluation records with classification for each item
2. Metrics computation (correct, missing, hallucinated, partial)
3. Structured result storage
4. Result serialization and analysis

Why separate from evaluation_structure.py and evaluation_business.py:
- Those modules compute metrics (line overlap, token similarity)
- This module handles result tracking and reporting
- Separation allows for flexible result storage formats
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class EvaluationResult:
    """Detailed evaluation result for a single run.

    Captures:
    - Model and strategy used
    - Task type (structure or business)
    - File processed
    - LLM output (raw and parsed)
    - Ground truth annotation
    - Classification for each predicted item
    - Aggregated metrics
    """

    def __init__(
        self,
        model: str,
        prompt_strategy: str,
        task: str,
        file: str,
        validation_status: str,
    ):
        self.model = model
        self.prompt_strategy = prompt_strategy
        self.task = task
        self.file = file
        self.validation_status = validation_status
        self.timestamp = datetime.utcnow().isoformat() + "Z"

        # Detailed results
        self.llm_output: Optional[Dict[str, Any]] = None
        self.ground_truth: Optional[Dict[str, Any]] = None
        self.evaluation_details: List[Dict[str, Any]] = []

        # Metrics
        self.metrics = {
            "correct": 0,
            "missing": 0,
            "hallucinated": 0,
            "partial": 0,
        }

    def add_correct(self, predicted: Any, matched_truth: Any, similarity_score: float = 1.0):
        """Record a correct prediction."""
        self.evaluation_details.append({
            "predicted": predicted,
            "matched_ground_truth": matched_truth,
            "status": "correct",
            "similarity_score": similarity_score,
        })
        self.metrics["correct"] += 1

    def add_partial(self, predicted: Any, matched_truth: Any, similarity_score: float):
        """Record a partial match (found but with lower similarity)."""
        self.evaluation_details.append({
            "predicted": predicted,
            "matched_ground_truth": matched_truth,
            "status": "partial",
            "similarity_score": similarity_score,
        })
        self.metrics["partial"] += 1

    def add_missing(self, ground_truth: Any):
        """Record a missing prediction (ground truth not found)."""
        self.evaluation_details.append({
            "predicted": None,
            "matched_ground_truth": ground_truth,
            "status": "missing",
            "similarity_score": 0.0,
        })
        self.metrics["missing"] += 1

    def add_hallucinated(self, predicted: Any):
        """Record a hallucinated prediction (predicted but no match in ground truth)."""
        self.evaluation_details.append({
            "predicted": predicted,
            "matched_ground_truth": None,
            "status": "hallucinated",
            "similarity_score": 0.0,
        })
        self.metrics["hallucinated"] += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model": self.model,
            "prompt_strategy": self.prompt_strategy,
            "task": self.task,
            "file": self.file,
            "validation_status": self.validation_status,
            "timestamp": self.timestamp,
            "llm_output": self.llm_output,
            "ground_truth": self.ground_truth,
            "evaluation_details": self.evaluation_details,
            "metrics": self.metrics,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary metrics."""
        total_predicted = (
            self.metrics["correct"] +
            self.metrics["partial"] +
            self.metrics["hallucinated"]
        )
        total_ground_truth = (
            self.metrics["correct"] +
            self.metrics["partial"] +
            self.metrics["missing"]
        )

        # Compute derived metrics
        precision = (
            self.metrics["correct"] / total_predicted
            if total_predicted > 0 else 0.0
        )
        recall = (
            (self.metrics["correct"] + self.metrics["partial"]) / total_ground_truth
            if total_ground_truth > 0 else 0.0
        )
        hallucination_rate = (
            self.metrics["hallucinated"] / total_predicted
            if total_predicted > 0 else 0.0
        )

        return {
            "metrics": self.metrics,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "hallucination_rate": round(hallucination_rate, 4),
            "total_predicted": total_predicted,
            "total_ground_truth": total_ground_truth,
        }


def build_evaluation_result(
    model: str,
    prompt_strategy: str,
    task: str,
    file: str,
    validation_status: str,
    llm_output: Dict[str, Any],
    ground_truth: Dict[str, Any],
    evaluation_report: Dict[str, Any],
) -> EvaluationResult:
    """Build an EvaluationResult from evaluation_structure/business output.

    Args:
        model: Model name
        prompt_strategy: Prompt strategy used
        task: Task type ("structure" or "business")
        file: File name processed
        validation_status: Schema validation status
        llm_output: Parsed LLM output
        ground_truth: Annotated ground truth
        evaluation_report: Report from evaluate_structure() or evaluate_business()
                          Must contain "summary" and "details" keys

    Returns:
        EvaluationResult with all details populated
    """
    result = EvaluationResult(model, prompt_strategy, task, file, validation_status)
    result.llm_output = llm_output
    result.ground_truth = ground_truth

    # Populate metrics from summary
    summary = evaluation_report.get("summary", {})
    details = evaluation_report.get("details", {})

    result.metrics["correct"] = summary.get("correct", 0)
    result.metrics["partial"] = summary.get("partial", 0)
    result.metrics["missing"] = summary.get("missing", 0)
    result.metrics["hallucinated"] = summary.get("hallucinated", 0)

    # Populate evaluation_details from details
    for correct_item in details.get("correct", []):
        predicted = correct_item.get("inferred") or correct_item.get("predicted")
        matched = correct_item.get("annotated") or correct_item.get("matched_ground_truth")
        score = correct_item.get("name_score") or correct_item.get("text_score", 1.0)
        result.add_correct(predicted, matched, score)

    for partial_item in details.get("partial", []):
        predicted = partial_item.get("inferred") or partial_item.get("predicted")
        matched = partial_item.get("annotated") or partial_item.get("matched_ground_truth")
        score = partial_item.get("name_score") or partial_item.get("text_score", 0.5)
        result.add_partial(predicted, matched, score)

    for missing_item in details.get("missing", []):
        result.add_missing(missing_item)

    for hallucinated_item in details.get("hallucinated", []):
        result.add_hallucinated(hallucinated_item)

    return result
