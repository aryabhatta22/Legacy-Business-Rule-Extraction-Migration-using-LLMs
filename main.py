import json
import os
from typing import Dict, Any, List, Optional

from evaluation.evaluation_business import evaluate_business
from evaluation.evaluation_structure import evaluate_structure
from experiments import experiments_log
from experiments.constants import FILE_PATHS
from experiments.pipeline_logger import get_logger, init_logger
from pipeline.evaluation import build_evaluation_result
from pipeline.llm_call import LLMCaller
from pipeline.llm_factory import LLM_Factory
from pipeline.load_data import load_all_programs
from pipeline.result_reporter import ResultReporter
from schema.business_logic import BusinessLogicOutput
from schema.program_structure import StructureOutput


USE_LLM = os.getenv("USE_LLM", "0") == "1"

# Comma-separated program names (e.g. PROGRAMS=VSCBEX01 or PROGRAMS=VSCBEX01,VSCBEX03).
# Empty/unset means run all programs. Lets dev/test runs hit the API for a single
# program instead of the full matrix.
PROGRAM_FILTER = {
    name.strip().upper()
    for name in os.getenv("PROGRAMS", "").split(",")
    if name.strip()
}


def _read_prompts(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _cobol_code_from_lines(cobol_obj: dict) -> str:
    """Join COBOL source lines, prefixing each with its absolute line number.

    Ground-truth line references and the evaluators' line-overlap gate use
    absolute line numbers, so the model must see them — without the prefix,
    models can only guess line positions and evidence matching fails.
    """
    lines = cobol_obj.get("lines", {})
    return "\n".join(f"{key}: {lines[key]}" for key in sorted(lines.keys()))


def _fill_prompt(template: str, program: str, code: str) -> str:
    """Substitute {program} and {code} without interpreting other braces.

    str.format() treats every {…} as a placeholder, which breaks templates
    that embed literal JSON examples. Simple replace() is unambiguous.
    """
    return template.replace("{program}", program).replace("{code}", code)


def _get_model_runs() -> List[Dict[str, Any]]:
    """Return live models or a deterministic dry-run placeholder."""
    if USE_LLM:
        return LLM_Factory.get_AllModels()

    return [
        {
            "ServiceName": "DRY_RUN",
            "modelArgs": {"model": "annotated-baseline"},
            "modelInstance": None,
        }
    ]


def _model_label(model: Dict[str, Any]) -> str:
    """Prefer the exact model id when it is available."""
    model_args = model.get("modelArgs", {})
    return model_args.get("model") or model.get("ServiceName", "unknown-model")


def _parsed_model_to_dict(parsed_model: Any) -> Optional[Dict[str, Any]]:
    """Convert a validated Pydantic model into a plain dictionary."""
    if parsed_model is None:
        return None
    if hasattr(parsed_model, "model_dump"):
        return parsed_model.model_dump()
    if hasattr(parsed_model, "dict"):
        return parsed_model.dict()
    if isinstance(parsed_model, dict):
        return parsed_model
    return None


def _serialize_raw_response(raw: Any) -> Optional[str]:
    """Flatten the agent's raw response into text safe for results.json.

    LLMCaller returns the agent's raw invoke() result — a dict holding LangChain
    message objects. Dumping that directly would store object reprs, which are
    useless for re-parsing. The final message's content is the pre-parse text
    needed to debug JSON-extraction and schema-validation failures.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        messages = raw.get("messages")
        if messages:
            content = getattr(messages[-1], "content", messages[-1])
            return content if isinstance(content, str) else str(content)
        return str(raw)
    return str(raw)


def _empty_evaluation_report() -> Dict[str, Any]:
    """Return an empty report with the same shape as the evaluators."""
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


def _select_inferred_output(
    parsed_output: Optional[Dict[str, Any]], annotation: Dict[str, Any]
) -> Dict[str, Any]:
    """Choose the evaluation input without leaking ground truth into live runs.

    When USE_LLM=0 we intentionally use the annotations as a dry-run baseline so
    the pipeline can exercise logging, evaluation, and artifact writing without
    requiring a network call. In live runs, invalid model output must not fall
    back to annotations because that would hide failures and corrupt metrics.
    """
    if parsed_output is not None:
        return parsed_output
    if not USE_LLM:
        return annotation or {}
    return {}


def _record_result(
    reporter: ResultReporter,
    program_name: str,
    model_name: str,
    strategy: str,
    task: str,
    validation_status: str,
    parsed_output: Optional[Dict[str, Any]],
    annotated: Dict[str, Any],
    eval_report: Dict[str, Any],
    complexity: Optional[str] = None,
    raw_response: Optional[str] = None,
    error_message: Optional[str] = None,
):
    """Store the same per-run record in both detailed and JSONL summaries."""
    result = build_evaluation_result(
        model=model_name,
        prompt_strategy=strategy,
        task=task,
        file=program_name,
        validation_status=validation_status,
        llm_output=parsed_output,
        ground_truth=annotated,
        evaluation_report=eval_report,
        complexity=complexity,
        raw_response=raw_response,
        error_message=error_message,
    )
    result_dict = result.to_dict()
    reporter.add_result(result_dict)

    experiments_log.log_result(
        {
            "program": program_name,
            "task": task,
            "prompt_strategy": strategy,
            "model": model_name,
            "validation_status": validation_status,
            "evaluation": eval_report.get("summary", {}),
            "metrics": result_dict.get("metrics", {}),
        }
    )


def main():
    init_logger()
    logger = get_logger()
    experiments_log.reset_log()
    reporter = ResultReporter()

    logger.pipeline_start()
    logger.info(f"USE_LLM={USE_LLM}", indent=0)

    base = os.getcwd()
    cobol_dir = os.path.join(base, FILE_PATHS["COBOL_PROGRAM_DIR"])
    annotations_base = os.path.join(base, "assets", "raw")
    prompts_dir = os.path.join(base, "prompts")

    structure_prompts = _read_prompts(os.path.join(prompts_dir, "structure_prompts.json"))
    business_prompts = _read_prompts(os.path.join(prompts_dir, "business_prompts.json"))
    programs = load_all_programs(cobol_dir, annotations_base)
    if PROGRAM_FILTER:
        programs = [p for p in programs if p["program"].upper() in PROGRAM_FILTER]
        logger.info(f"PROGRAMS filter active: {sorted(PROGRAM_FILTER)}", indent=0)
    model_runs = _get_model_runs()
    if USE_LLM and not model_runs:
        # LLM_Factory silently skips families without an API key; a live run
        # with zero models would "succeed" with empty artifacts otherwise.
        logger.error(
            "USE_LLM=1 but no models were configured — is OPENROUTER_API_KEY set?",
            indent=0,
        )
        raise SystemExit(1)

    logger.programs_loaded(len(programs))

    for program in programs:
        program_name = program["program"]
        cobol_code = _cobol_code_from_lines(program["cobol"])
        # Complexity label is read once per program from the annotation file and
        # passed to every run so it appears in all result rows for this program.
        complexity = program.get("complexity")
        logger.program_start(program_name)

        for strategy, template in structure_prompts.get("strategies", {}).items():
            logger.task_start("structure", strategy)
            prompt = _fill_prompt(template, program_name, cobol_code)
            annotated = program.get("structure_annotation") or {}

            for model in model_runs:
                service_name = model.get("ServiceName", "UNKNOWN")
                model_args = model.get("modelArgs", {})
                model_instance = model.get("modelInstance")
                model_name = _model_label(model)
                logger.model_start(f"{service_name} | {model_name}")

                # Reset every run-specific variable inside the model loop so one
                # model cannot leak parsed output, status, or metrics into the next.
                parsed = None
                raw_response = None
                error_message = None
                validation_status = "skipped"
                eval_report = _empty_evaluation_report()

                if USE_LLM and model_instance is not None:
                    logger.llm_call_start()
                    llm_caller = LLMCaller(
                        model_instance,
                        StructureOutput,
                        task_name=f"structure evaluation for {model_name}",
                    )
                    response = llm_caller.call(
                        prompt,
                        max_retries=model_args.get("max_retries", 1),
                    )
                    parsed = _parsed_model_to_dict(response.get("parsed"))
                    raw_response = _serialize_raw_response(response.get("raw"))
                    error_message = response.get("exception") or response.get(
                        "validation_error"
                    )

                    if response.get("success") and parsed is not None:
                        validation_status = "valid"
                    elif response.get("exception"):
                        validation_status = "error"
                        logger.schema_validation(False, "no parsed output after LLM error")
                    else:
                        validation_status = "invalid"
                else:
                    logger.info(
                        "Using annotated baseline because USE_LLM=0",
                        indent=3,
                    )

                inferred = _select_inferred_output(parsed, annotated)
                if annotated:
                    eval_report = evaluate_structure(inferred, annotated)
                else:
                    logger.warn("No structure annotation found; evaluation skipped", indent=3)

                _record_result(
                    reporter=reporter,
                    program_name=program_name,
                    model_name=model_name,
                    strategy=strategy,
                    task="structure",
                    validation_status=validation_status,
                    parsed_output=parsed,
                    annotated=annotated,
                    eval_report=eval_report,
                    complexity=complexity,
                    raw_response=raw_response,
                    error_message=error_message,
                )
                logger.evaluation_complete(eval_report.get("summary", {}))

        for strategy, template in business_prompts.get("strategies", {}).items():
            logger.task_start("business", strategy)
            prompt = _fill_prompt(template, program_name, cobol_code)
            annotated = program.get("business_annotation") or {}

            for model in model_runs:
                service_name = model.get("ServiceName", "UNKNOWN")
                model_args = model.get("modelArgs", {})
                model_instance = model.get("modelInstance")
                model_name = _model_label(model)
                logger.model_start(f"{service_name} | {model_name}")

                # Keep the business task isolated for the same reason as the
                # structure task: every model run must start from a clean slate.
                parsed = None
                raw_response = None
                error_message = None
                validation_status = "skipped"
                eval_report = _empty_evaluation_report()

                if USE_LLM and model_instance is not None:
                    logger.llm_call_start()
                    llm_caller = LLMCaller(
                        model_instance,
                        BusinessLogicOutput,
                        task_name=f"business evaluation for {model_name}",
                    )
                    response = llm_caller.call(
                        prompt,
                        max_retries=model_args.get("max_retries", 1),
                    )
                    parsed = _parsed_model_to_dict(response.get("parsed"))
                    raw_response = _serialize_raw_response(response.get("raw"))
                    error_message = response.get("exception") or response.get(
                        "validation_error"
                    )

                    if response.get("success") and parsed is not None:
                        validation_status = "valid"
                    elif response.get("exception"):
                        validation_status = "error"
                        logger.schema_validation(False, "no parsed output after LLM error")
                    else:
                        validation_status = "invalid"
                else:
                    logger.info(
                        "Using annotated baseline because USE_LLM=0",
                        indent=3,
                    )

                inferred = _select_inferred_output(parsed, annotated)
                if annotated:
                    eval_report = evaluate_business(inferred, annotated)
                else:
                    logger.warn("No business annotation found; evaluation skipped", indent=3)

                _record_result(
                    reporter=reporter,
                    program_name=program_name,
                    model_name=model_name,
                    strategy=strategy,
                    task="business",
                    validation_status=validation_status,
                    parsed_output=parsed,
                    annotated=annotated,
                    eval_report=eval_report,
                    complexity=complexity,
                    raw_response=raw_response,
                    error_message=error_message,
                )
                logger.evaluation_complete(eval_report.get("summary", {}))

    reporter.save_json()
    reporter.save_csv()
    reporter.save_summary()
    reporter.generate_extended_outputs()
    reporter.print_summary()
    logger.pipeline_end()


if __name__ == "__main__":
    main()
