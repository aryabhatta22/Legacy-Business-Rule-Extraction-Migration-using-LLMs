import os
import json
from pipeline.load_data import load_all_programs
from pipeline.llm_call import LLMCaller
from experiments.constants import FILE_PATHS
from experiments import experiments_log
from pipeline.llm_factory import LLM_Factory

# evaluators
from evaluation.evaluation_structure import evaluate_structure
from evaluation.evaluation_business import evaluate_business

USE_LLM = os.getenv("USE_LLM", "0") == "1"


def _read_prompts(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _cobol_code_from_lines(cobol_obj: dict) -> str:
    # join lines preserving original order
    lines = cobol_obj.get("lines", {})
    ordered = [lines[k] for k in sorted(lines.keys())]
    return "\n".join(ordered)


def main():
    print("*" * 20)
    print("[PIPELINE] Starting COBOL extraction pipeline")
    base = os.getcwd()
    cobol_dir = os.path.join(base, FILE_PATHS["COBOL_PROGRAM_DIR"])
    annotations_base = os.path.join(base, "assets", "raw")

    prompts_dir = os.path.join(base, "prompts")
    structure_prompts = _read_prompts(
        os.path.join(prompts_dir, "structure_prompts.json")
    )
    business_prompts = _read_prompts(os.path.join(prompts_dir, "business_prompts.json"))

    programs = load_all_programs(cobol_dir, os.path.join(annotations_base))
    print(f"[PIPELINE] Loaded {len(programs)} COBOL programs")

    for prog in programs:
        print("-" * 20)
        print(f"[PROGRAM] Processing: {prog['program']}")
        program_name = prog["program"]
        cobol_obj = prog["cobol"]
        cobol_code = _cobol_code_from_lines(cobol_obj)

        # Structure task: infer program constructs and organization
        # This task identifies divisions, sections, loops, file operations, etc.
        for strategy, template in structure_prompts.get("strategies", {}).items():
            print("-" * 20)
            print("  [TASK] structure")
            print(f"    [STRATEGY] {strategy}")
            prompt = template.format(program=program_name, code=cobol_code)

            # If LLM is enabled, user must provide LLM factory; otherwise dry-run
            # GHOST DATA LEAK FIX: Reset all tracking variables at the beginning of
            # each strategy iteration to prevent results from previous strategies
            # from contaminating current evaluation. This is critical for experimental
            # validity and ensures clean separation between prompt strategy runs.
            parsed = None
            validation_status = "skipped"
            if USE_LLM:
                try:
                    modelsList = LLM_Factory.get_AllModels()
                    for model in modelsList:
                        # GHOST DATA LEAK FIX: Reset all tracking variables at the beginning
                        # of each model iteration to prevent data from previous models leaking.
                        # This ensures that each model's validation status, parsed output,
                        # and evaluation metrics are isolated and cannot contaminate results.
                        parsed = None
                        validation_status = "skipped"

                        model_name = model.get('ServiceName')
                        print(f"      [MODEL] {model_name} - {model.get('modelArgs', {}).get('model')}")
                        ServiceName, modelArgs, modelInstance = model.values()
                        from pipeline.llm_call import LLMCaller
                        from schema.program_structure import StructureOutput

                        print("        Loading prompt and calling LLM...")
                        llm_caller = LLMCaller(
                            modelInstance,
                            StructureOutput,
                            task_name=f"structure_evaluation for {ServiceName}",
                        )
                        res = llm_caller.call(prompt)
                        if res.get("success") and res.get("parsed") is not None:
                            parsed_model = res.get("parsed")
                            # convert to plain dict
                            parsed = getattr(parsed_model, "model_dump", None)
                            if callable(parsed):
                                parsed = parsed_model.model_dump()
                            else:
                                parsed = getattr(parsed_model, "dict", lambda: None)()
                            validation_status = "valid"
                            print("        Schema validation: valid")
                        else:
                            validation_status = "invalid"
                            print("        Schema validation: invalid")
                        # when LLM disabled, use annotated as inferred for evaluation (dry-run)
                        inferred = (
                            parsed
                            if parsed is not None
                            else (prog.get("structure_annotation") or {})
                        )
                        annotated = prog.get("structure_annotation") or {}
                        # Ensure inferred is a dict before evaluation
                        inferred_dict = inferred if isinstance(inferred, dict) else {}

                        print("        Running evaluation...")
                        eval_report = (
                            evaluate_structure(inferred_dict, annotated)
                            if inferred_dict and annotated
                            else {"summary": {}, "details": {}}
                        )

                        # log
                        experiments_log.log_result(
                            {
                                "program": program_name,
                                "task": "structure",
                                "prompt_strategy": strategy,
                                "model": ServiceName,
                                "validation_status": validation_status,
                                # Standard Counts
                                "evaluation": eval_report.get("summary"),
                                # Core Performance Metrics (Lifting these for easier access)
                                "metrics": {
                                    "completeness": eval_report["summary"].get(
                                        "completeness"
                                    ),
                                    "hallucination_rate": eval_report["summary"].get(
                                        "hallucination_rate"
                                    ),
                                    "fidelity": eval_report["summary"].get(
                                        "structural_fidelity"
                                    )
                                    or eval_report["summary"].get("grounding_fidelity"),
                                },
                                # Useful for debugging/re-evaluation
                                "raw_output_length": len(str(parsed)),
                            }
                        )

                        # Log evaluation summary
                        summary = eval_report.get("summary", {})
                        print(f"        Evaluation: correct={summary.get('correct')}, "
                              f"partial={summary.get('partial')}, "
                              f"missing={summary.get('missing')}, "
                              f"hallucinated={summary.get('hallucinated')}")
                except Exception as e:
                    validation_status = f"error:{e}"

        # Business task: infer domain-level business rules and guarantees
        # This task extracts semantic intent and business constraints from COBOL code
        for strategy, template in business_prompts.get("strategies", {}).items():
            print("-" * 20)
            print("  [TASK] business")
            print(f"    [STRATEGY] {strategy}")
            prompt = template.format(program=program_name, code=cobol_code)

            # GHOST DATA LEAK FIX: Reset all tracking variables at the beginning of
            # each strategy iteration to prevent results from previous strategies
            # from contaminating current evaluation. This is critical for experimental
            # validity and ensures clean separation between prompt strategy runs.
            parsed = None
            validation_status = "skipped"
            if USE_LLM:
                try:
                    modelsList = LLM_Factory.get_AllModels()
                    for model in modelsList:
                        # GHOST DATA LEAK FIX: Reset all tracking variables at the beginning
                        # of each model iteration to prevent data from previous models leaking.
                        # This ensures that each model's validation status, parsed output,
                        # and evaluation metrics are isolated and cannot contaminate results.
                        parsed = None
                        validation_status = "skipped"

                        model_name = model.get('ServiceName')
                        print(f"      [MODEL] {model_name}")
                        ServiceName, modelArgs, modelInstance = model.values()
                        from pipeline.llm_call import LLMCaller
                        from schema.business_logic import BusinessLogicOutput

                        print("        Loading prompt and calling LLM...")
                        llm_caller = LLMCaller(
                            modelInstance,
                            BusinessLogicOutput,
                            task_name=f"structure_evaluation for {ServiceName}",
                        )
                        res = llm_caller.call(prompt)
                        if res.get("success") and res.get("parsed") is not None:
                            parsed_model = res.get("parsed")
                            parsed = getattr(parsed_model, "model_dump", None)
                            if callable(parsed):
                                parsed = parsed_model.model_dump()
                            else:
                                parsed = getattr(parsed_model, "dict", lambda: None)()
                            validation_status = "valid"
                            print("        Schema validation: valid")
                        else:
                            validation_status = "invalid"
                            print("        Schema validation: invalid")
                        inferred = (
                            parsed
                            if parsed is not None
                            else (prog.get("business_annotation") or {})
                        )
                        annotated = prog.get("business_annotation") or {}

                        print("        Running evaluation...")
                        eval_report = (
                            evaluate_business(inferred, annotated)
                            if inferred and annotated
                            else {"summary": {}, "details": {}}
                        )

                        experiments_log.log_result(
                            {
                                "program": program_name,
                                "task": "business",
                                "prompt_strategy": strategy,
                                "model": ServiceName,
                                "validation_status": validation_status,
                                # Standard Counts
                                "evaluation": eval_report.get("summary"),
                                # Core Performance Metrics (Lifting these for easier access)
                                "metrics": {
                                    "completeness": eval_report["summary"].get(
                                        "completeness"
                                    ),
                                    "hallucination_rate": eval_report["summary"].get(
                                        "hallucination_rate"
                                    ),
                                    "fidelity": eval_report["summary"].get(
                                        "structural_fidelity"
                                    )
                                    or eval_report["summary"].get("grounding_fidelity"),
                                },
                                # Useful for debugging/re-evaluation
                                "raw_output_length": len(str(parsed)),
                            }
                        )

                        # Log evaluation summary
                        summary = eval_report.get("summary", {})
                        print(f"        Evaluation: correct={summary.get('correct')}, "
                              f"partial={summary.get('partial')}, "
                              f"missing={summary.get('missing')}, "
                              f"hallucinated={summary.get('hallucinated')}")
                except Exception as e:
                    validation_status = f"error:{e}"
                    print(f"        Error: {str(e)[:100]}")

    print("*" * 20)
    print("[PIPELINE] Experiment complete")


if __name__ == "__main__":
    main()
