# COBOL LLM Evaluation Harness

This repository runs controlled experiments for two separate COBOL analysis
tasks:

1. Program structure extraction
2. Business logic extraction

The code is intentionally minimal. It uses existing Pydantic schemas, prompt
templates, and evaluation modules so model runs can be compared consistently.

## Pipeline Overview

For each COBOL program, prompt strategy, and model, the pipeline:

1. Builds the prompt from the source code and prompt template
2. Calls the LLM
3. Extracts JSON from the response
4. Validates the JSON against the task schema
5. Evaluates the parsed output against annotated JSON
6. Writes logs and result artifacts under `experiments/`

The structure and business tasks remain independent. They are evaluated and
stored separately.

## JSON Extraction

`pipeline/llm_call.py` uses a simple, reproducible extraction strategy:

1. Remove surrounding Markdown code fences when present
2. Find the first `{` and the last `}`
3. Parse only that substring with `json.loads`
4. Log success or failure to the console and `experiments/run_log.txt`

This keeps extraction easy to debug. It avoids trying multiple parsing
strategies that can hide formatting failures.

## Evaluation Method

### Structure Evaluation

`evaluation/evaluation_structure.py` matches annotated structures to inferred
structures using three signals:

1. Type compatibility
2. Positive line overlap
3. Name similarity as a tie-breaker

Rules:

- Matching is one-to-one. A single inferred structure cannot satisfy multiple
  annotated structures.
- Type compatibility is required before a match is considered.
- A match is `correct` when type is compatible, line overlap is positive, and
  normalized name overlap is `>= 0.5`.
- A match is `partial` when type is compatible and lines overlap, but the name
  score is below `0.5`.
- Annotated items without a match are `missing`.
- Unmatched inferred items are `hallucinated`.

The evaluator uses the following compatibility map:

- `DIVISION -> METADATA, CONFIGURATION, DATA`
- `SECTION -> FILE_DEFINITION, STORAGE, DECLARATION`
- `PARAGRAPH -> ENTRY_POINT, INITIALIZATION, PROCESSING, TERMINATION, DATA_DEFINITION, DATA_INITIALIZATION, DATA_MODIFICATION, DATA_TRANSFORMATION, I_O, FILE_IO`
- `LOOP -> LOOP, CONTROL_FLOW`
- `FILE_OP -> FILE_DEFINITION, FILE_IO, I_O`
- `CONDITIONAL -> CONTROL_FLOW`

### Business Logic Evaluation

`evaluation/evaluation_business.py` uses a hybrid matcher:

1. Positive evidence-line overlap is required
2. Candidate matches are ranked by `(line overlap, token Jaccard similarity)`
3. The text score is computed from normalized lowercase alphanumeric tokens

Rules:

- A match is `correct` when evidence overlaps and semantic score is `>= 0.5`
- A match is `partial` when evidence overlaps but semantic score is below `0.5`
- Annotated rules with no overlapping inferred rule are `missing`
- Unmatched inferred rules are `hallucinated`

This approach keeps business-rule evaluation simple and dependency-free while
still allowing paraphrasing.

## Logging

The pipeline uses the logger in `experiments/pipeline_logger.py`.

Output is written to:

- Console with indentation by pipeline stage
- `experiments/run_log.txt` for a persistent run trace

Logged stages include:

- Pipeline start and end
- Program start
- Task and prompt strategy
- Model start
- LLM call start
- JSON extraction success or failure
- Schema validation result
- Evaluation summary
- Artifact writes

`experiments/log.jsonl` is also rewritten each run as a lightweight JSON-lines
summary of per-run metrics.

## Results

Each run overwrites the main result artifacts so outputs stay reproducible:

- `experiments/results/results.json`
- `experiments/results/results_summary.csv`
- `experiments/results/summary.json`

### `results.json`

Contains one record per `(model, prompt_strategy, task, file)` run with:

- `model`
- `prompt_strategy`
- `task`
- `file`
- `validation_status`
- `timestamp`
- `llm_output`
- `ground_truth`
- `evaluation_details`
- `metrics`

Each `evaluation_details` item stores normalized comparison data:

- `status`
- `predicted`
- `matched_ground_truth`
- `overlap`
- `name_score` for structure matches or `semantic_score` for business matches

### `results_summary.csv`

Contains one summary row per run with:

- `model`
- `prompt_strategy`
- `task`
- `file`
- `validation_status`
- `correct`
- `partial`
- `missing`
- `hallucinated`
- `total_ground_truth`
- `total_predicted`
- `precision`
- `recall`
- `completeness`
- `hallucination_rate`
- `structural_fidelity` when available

## Metric Definitions

Shared metrics are computed from the evaluation counts:

- `correct`: matched items meeting the task threshold
- `partial`: matched items with grounding overlap but weaker semantic/name match
- `missing`: annotated items with no acceptable inferred match
- `hallucinated`: inferred items with no annotated match
- `total_ground_truth = correct + partial + missing`
- `total_predicted = correct + partial + hallucinated`
- `precision = correct / total_predicted`
- `recall = correct / total_ground_truth`
- `completeness = (correct + partial) / total_ground_truth`
- `hallucination_rate = hallucinated / total_predicted`

Task-specific metrics may also appear in `metrics`, such as
`structural_fidelity` for structure runs.

## Reproducibility Notes

- The pipeline resets per-model state inside each model loop so one run cannot
  leak parsed output or validation state into the next.
- Invalid LLM output is not replaced with annotations during live runs.
- When `USE_LLM=0`, the pipeline uses annotated data as a dry-run baseline so
  evaluation, logging, and artifact generation can be tested without model
  access.

## Running the Pipeline

Install dependencies:

```bash
uv sync
```

Dry run without calling a model:

```bash
uv run main.py
```

Run with LLM access enabled:

```bash
USE_LLM=1 uv run main.py
```

## Repository Layout

```text
assets/raw/                 Source COBOL and annotations
evaluation/                 Structure and business evaluators
experiments/                Logs and result artifacts
pipeline/                   LLM call, evaluation result, and reporting helpers
prompts/                    Prompt strategies
schema/                     Pydantic output schemas
main.py                     Experiment entrypoint
```
