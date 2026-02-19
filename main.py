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
    base = os.getcwd()
    cobol_dir = os.path.join(base, FILE_PATHS["COBOL_PROGRAM_DIR"])
    annotations_base = os.path.join(base, "assets", "raw")

    prompts_dir = os.path.join(base, "prompts")
    structure_prompts = _read_prompts(
        os.path.join(prompts_dir, "structure_prompts.json")
    )
    business_prompts = _read_prompts(os.path.join(prompts_dir, "business_prompts.json"))

    programs = load_all_programs(cobol_dir, os.path.join(annotations_base))

    for prog in programs:
        program_name = prog["program"]
        cobol_obj = prog["cobol"]
        cobol_code = _cobol_code_from_lines(cobol_obj)

        # Structure task
        for strategy, template in structure_prompts.get("strategies", {}).items():
            prompt = template.format(program=program_name, code=cobol_code)
            # If LLM is enabled, user must provide LLM factory; otherwise dry-run
            parsed = None
            validation_status = "skipped"
            if USE_LLM:
                try:
                    modelsList = LLM_Factory.get_AllModels()
                    for model in modelsList:
                        ServiceName, modelArgs, modelInstance = model.values()
                        from pipeline.llm_call import LLMCaller
                        from schema.program_structure import StructureOutput

                        llm_caller = LLMCaller(
                            modelInstance,
                            StructureOutput,
                            task_name=f"structure_evaluation for {ServiceName} under args {str(modelArgs)}",
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
                        else:
                            validation_status = "invalid"
                        # when LLM disabled, use annotated as inferred for evaluation (dry-run)
                        inferred = (
                            parsed
                            if parsed is not None
                            else (prog.get("structure_annotation") or {})
                        )
                        annotated = prog.get("structure_annotation") or {}
                        # Ensure inferred is a dict before evaluation
                        inferred_dict = inferred if isinstance(inferred, dict) else {}
                        eval_report = (
                            evaluate_structure(inferred_dict, annotated)
                            if inferred_dict and annotated
                            else {"summary": {}, "details": {}}
                        )

                        # log
                        experiments_log.log_result(
                            {
                                "modelLevelInfo": {
                                    "model": ServiceName,
                                    "model_args": modelArgs,
                                    "structured_output": parsed,
                                },
                                "task": "structure",
                                "prompt_strategy": strategy,
                                "program": program_name,
                                "validation_status": validation_status,
                                "evaluation": eval_report.get("summary"),
                            }
                        )
                except Exception as e:
                    validation_status = f"error:{e}"

        # Business task
        for strategy, template in business_prompts.get("strategies", {}).items():
            prompt = template.format(program=program_name, code=cobol_code)
            parsed = None
            validation_status = "skipped"
            if USE_LLM:
                try:
                    modelsList = LLM_Factory.get_AllModels()
                    for model in modelsList:
                        ServiceName, modelArgs, modelInstance = model.values()
                        from pipeline.llm_call import LLMCaller
                        from schema.business_logic import BusinessLogicOutput

                        llm_caller = LLMCaller(
                            modelInstance,
                            BusinessLogicOutput,
                            task_name=f"structure_evaluation for {ServiceName} under args {str(modelArgs)}",
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
                        else:
                            validation_status = "invalid"
                        inferred = (
                            parsed
                            if parsed is not None
                            else (prog.get("business_annotation") or {})
                        )
                        annotated = prog.get("business_annotation") or {}
                        eval_report = (
                            evaluate_business(inferred, annotated)
                            if inferred and annotated
                            else {"summary": {}, "details": {}}
                        )

                        experiments_log.log_result(
                            {
                                "modelLevelInfo": {
                                    "model": ServiceName,
                                    "model_args": modelArgs,
                                    "structured_output": parsed,
                                },
                                "task": "business",
                                "prompt_strategy": strategy,
                                "program": program_name,
                                "validation_status": validation_status,
                                "evaluation": eval_report.get("summary"),
                            }
                        )
                except Exception as e:
                    validation_status = f"error:{e}"


if __name__ == "__main__":
    main()
