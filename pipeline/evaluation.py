"""Detailed evaluation result tracking and reporting."""

from typing import Dict, Any, List, Optional
from datetime import datetime


class EvaluationResult:
    """Detailed evaluation result for a single run."""

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

        self.llm_output: Optional[Dict[str, Any]] = None
        self.ground_truth: Optional[Dict[str, Any]] = None
        self.evaluation_details: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {
            "correct": 0,
            "partial": 0,
            "missing": 0,
            "hallucinated": 0,
            "total_ground_truth": 0,
            "total_predicted": 0,
            "precision": 0.0,
            "recall": 0.0,
            "completeness": 0.0,
            "hallucination_rate": 0.0,
        }

    def add_detail(
        self,
        status: str,
        predicted: Any,
        matched_truth: Any,
        overlap: int,
        similarity_field: Optional[str],
        similarity_score: float,
    ):
        """Add a normalized evaluation detail row."""
        detail = {
            "status": status,
            "predicted": predicted,
            "matched_ground_truth": matched_truth,
            "overlap": overlap,
        }
        if similarity_field:
            detail[similarity_field] = similarity_score
        self.evaluation_details.append(detail)

    def finalize_metrics(self, evaluation_summary: Dict[str, Any]):
        """Compute shared metrics and preserve task-specific summary values."""
        counts = {
            "correct": evaluation_summary.get("correct", 0),
            "partial": evaluation_summary.get("partial", 0),
            "missing": evaluation_summary.get("missing", 0),
            "hallucinated": evaluation_summary.get("hallucinated", 0),
        }

        total_ground_truth = (
            evaluation_summary.get("total_ground_truth")
            or counts["correct"] + counts["partial"] + counts["missing"]
        )
        total_predicted = (
            evaluation_summary.get("total_predicted")
            or counts["correct"] + counts["partial"] + counts["hallucinated"]
        )

        precision = counts["correct"] / total_predicted if total_predicted > 0 else 0.0
        recall = counts["correct"] / total_ground_truth if total_ground_truth > 0 else 0.0
        completeness = (
            (counts["correct"] + counts["partial"]) / total_ground_truth
            if total_ground_truth > 0
            else 0.0
        )
        hallucination_rate = (
            counts["hallucinated"] / total_predicted if total_predicted > 0 else 0.0
        )

        self.metrics = {
            **counts,
            "total_ground_truth": total_ground_truth,
            "total_predicted": total_predicted,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "completeness": round(completeness, 4),
            "hallucination_rate": round(hallucination_rate, 4),
        }

        # Preserve any task-specific metrics such as structural_fidelity.
        for key, value in evaluation_summary.items():
            if key not in self.metrics:
                self.metrics[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a JSON-serializable dictionary."""
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


def build_evaluation_result(
    model: str,
    prompt_strategy: str,
    task: str,
    file: str,
    validation_status: str,
    llm_output: Optional[Dict[str, Any]],
    ground_truth: Dict[str, Any],
    evaluation_report: Dict[str, Any],
) -> EvaluationResult:
    """Build an EvaluationResult from evaluation output."""
    result = EvaluationResult(model, prompt_strategy, task, file, validation_status)
    result.llm_output = llm_output
    result.ground_truth = ground_truth

    summary = evaluation_report.get("summary", {})
    details = evaluation_report.get("details", {})

    for item in details.get("correct", []):
        result.add_detail(
            status="correct",
            predicted=item.get("inferred"),
            matched_truth=item.get("annotated"),
            overlap=item.get("overlap", 0),
            similarity_field="name_score" if "name_score" in item else "semantic_score",
            similarity_score=item.get("name_score", item.get("semantic_score", 0.0)),
        )

    for item in details.get("partial", []):
        result.add_detail(
            status="partial",
            predicted=item.get("inferred"),
            matched_truth=item.get("annotated"),
            overlap=item.get("overlap", 0),
            similarity_field="name_score" if "name_score" in item else "semantic_score",
            similarity_score=item.get("name_score", item.get("semantic_score", 0.0)),
        )

    for item in details.get("missing", []):
        result.add_detail(
            status="missing",
            predicted=item.get("inferred"),
            matched_truth=item.get("annotated"),
            overlap=item.get("overlap", 0),
            similarity_field="name_score" if "name_score" in item else "semantic_score",
            similarity_score=item.get("name_score", item.get("semantic_score", 0.0)),
        )

    for item in details.get("hallucinated", []):
        result.add_detail(
            status="hallucinated",
            predicted=item.get("inferred"),
            matched_truth=item.get("annotated"),
            overlap=item.get("overlap", 0),
            similarity_field="name_score" if "name_score" in item else "semantic_score",
            similarity_score=item.get("name_score", item.get("semantic_score", 0.0)),
        )

    result.finalize_metrics(summary)
    return result
