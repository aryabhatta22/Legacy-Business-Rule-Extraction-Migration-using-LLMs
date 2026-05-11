# COBOL LLM Benchmarking Framework

This repository is a reproducible benchmarking framework for evaluating large language models (LLMs) on COBOL legacy modernization tasks. It supports 160 experiment combinations across four models, four prompt strategies, two tasks, and five COBOL programs.

## Experiment Matrix

| Dimension | Options | Count |
|-----------|---------|-------|
| Models | GPT-4.1-mini, Gemma-3-27B, LLaMA-3.1-8B, Qwen-2.5-72B | 4 |
| Prompt strategies | direct, few_shot, cot, modular | 4 |
| Tasks | structure, business | 2 |
| COBOL files | VSCBEX01 – VSCBEX05 | 5 |
| **Total runs** | **4 × 4 × 2 × 5** | **160** |

All models are accessed through OpenRouter using a single `OPENROUTER_API_KEY`.

---

## Pipeline Overview

For each (model, prompt strategy, task, file) combination the pipeline:

1. Builds the prompt from the COBOL source and the prompt template
2. Calls the LLM via OpenRouter
3. Extracts JSON from the response using a brace-based strategy
4. Validates the JSON against the task Pydantic schema
5. Evaluates the parsed output against annotated ground truth
6. Records all metrics, writes logs and result artifacts

Structure and business tasks run independently in separate loops.

---

## Prompt Strategies

Four strategies are defined in `prompts/structure_prompts.json` and
`prompts/business_prompts.json` under the `"strategies"` key.
Templates use `{program}` and `{code}` placeholders injected at runtime.

| Strategy | Description |
|----------|-------------|
| `direct` | Minimal instruction — extract and return JSON |
| `few_shot` | Includes worked examples before the target program |
| `cot` | Uses hidden chain-of-thought reasoning before producing output |
| `modular` | Breaks extraction into labelled sub-steps within a single prompt |

Prompt files are loaded dynamically; adding a new strategy key requires no code change.

---

## Composite Benchmark Score (CBS)

CBS is the primary thesis metric. It combines precision, recall, completeness, and hallucination rate into a single comparable number.

```
CBS = 0.40 × Recall
    + 0.30 × Precision
    + 0.20 × (1 − Hallucination Rate)
    + 0.10 × Completeness
```

Recall carries the highest weight because missing ground-truth items is the most critical failure for legacy modernization. The `(1 − H)` term rewards low hallucination without double-penalising precision.

CBS is computed per run and appears in all result files and graphs.

---

## Metric Definitions

All metrics are defined consistently across the codebase and thesis.

| Metric | Formula |
|--------|---------|
| Precision | `correct / total_predicted` |
| Recall | `correct / total_ground_truth` |
| Completeness | `(correct + partial) / total_ground_truth` |
| Hallucination Rate | `hallucinated / total_predicted` |
| CBS | `0.40R + 0.30P + 0.20(1−H) + 0.10C` |
| Structural Fidelity | `correct_with_valid_parent / total_correct` |
| Avg Semantic | `mean(semantic_score of matched business-rule pairs)` |
| Schema Pass Rate | `valid_responses / total_responses` |

- `correct` — matches meeting the task threshold (name score ≥ 0.5 for structure; semantic score ≥ 0.5 for business)
- `partial` — matches with grounding overlap but weaker semantic / name similarity
- `missing` — annotated items with no acceptable inferred match
- `hallucinated` — inferred items with no annotated match

---

## Structure Evaluation

`evaluation/evaluation_structure.py` matches annotated structures to inferred structures using:

1. **Type compatibility** (required)
2. **Positive line overlap** (required)
3. **Name token overlap** (tie-breaker and correct / partial label)

Type compatibility map:

| Inferred type | Compatible annotated types |
|---------------|---------------------------|
| `DIVISION` | `METADATA`, `CONFIGURATION`, `DATA` |
| `SECTION` | `FILE_DEFINITION`, `STORAGE`, `DECLARATION` |
| `PARAGRAPH` | `ENTRY_POINT`, `INITIALIZATION`, `PROCESSING`, `TERMINATION`, `DATA_DEFINITION`, `DATA_INITIALIZATION`, `DATA_MODIFICATION`, `DATA_TRANSFORMATION`, `I_O`, `FILE_IO` |
| `LOOP` | `LOOP`, `CONTROL_FLOW` |
| `FILE_OP` | `FILE_DEFINITION`, `FILE_IO`, `I_O` |
| `CONDITIONAL` | `CONTROL_FLOW` |

### Structural Fidelity

For each correctly matched structure the evaluator checks whether the inferred
`parent_id` is also correct:

- Root structures (annotated types `METADATA`, `CONFIGURATION`, `DATA`) are correct when `parent_id` is null.
- Non-root structures are correct when `parent_id` points to another inferred structure that is itself correctly matched.

`structural_fidelity = correct_with_valid_parent / total_correct`

---

## Business Logic Evaluation

`evaluation/evaluation_business.py` uses a hybrid matcher:

1. Positive evidence-line overlap is required.
2. Candidates are ranked by `(line overlap, token Jaccard similarity)`.
3. Matching is one-to-one.

`avg_semantic` is the mean token Jaccard score across all matched (correct + partial) pairs
per run. It measures semantic faithfulness independently of recall.

---

## Complexity Labels

Each annotated program includes a `complexity.level` field (`simple`, `medium`, `complex`).
The pipeline reads this from `assets/raw/Annotated data/{program}.json` and stores it on
every result row, enabling complexity-stratified reporting.

---

## JSON Extraction

`pipeline/llm_call.py` uses a reproducible single-strategy extraction:

1. Strip surrounding Markdown code fences when present.
2. Find the first `{` and the last `}`.
3. Parse that substring with `json.loads`.

This avoids trying multiple strategies that can hide formatting failures.

---

## Logging

`experiments/pipeline_logger.py` provides a singleton logger that writes to both
the console (with stage indentation) and `experiments/run_log.txt`.

`experiments/log.jsonl` is reset at the start of each run and accumulates one
JSON-lines record per completed run.

---

## Result Files

All artifacts are written to `experiments/results/` at the end of each run.

### Per-run files

| File | Contents |
|------|----------|
| `results.json` | Detailed per-run records including `llm_output`, `ground_truth`, `evaluation_details`, and `metrics` |
| `results_summary.csv` | One row per run — all metrics including CBS, structural fidelity, avg semantic, schema pass rate, complexity |
| `summary.json` | Aggregate statistics grouped by (model, task) plus global totals including CBS |

### Aggregated tables

| File | Grouping |
|------|----------|
| `raw_results.csv` | One row per run — same columns as `results_summary.csv` |
| `aggregated_results.csv` | Grouped by (model, prompt_strategy) — mean metrics |
| `task_results.csv` | Grouped by (model, task) — mean metrics |
| `complexity_results.csv` | Grouped by (model, complexity) — mean metrics (written only when complexity labels are present) |

### Analysis summaries

| File | Contents |
|------|----------|
| `analysis_summary.json` | Best performer per metric: CBS, structural fidelity, schema pass rate, semantic faithfulness, hallucination |
| `analysis_summary.txt` | Human-readable equivalent for thesis appendix |

### Graphs

All charts are saved to `experiments/results/graphs/` at 150 dpi.

| File | Description |
|------|-------------|
| `cbs_ranking.png` | Horizontal bar chart: mean CBS per (model × prompt) group, sorted descending |
| `metric_comparison.png` | Grouped bar: precision, recall, completeness, hallucination per model |
| `hallucination_vs_cbs.png` | Scatter plot: hallucination rate (x) vs CBS (y), coloured by model |
| `prompt_strategy_comparison.png` | Mean CBS per prompt strategy, split by task |
| `cbs_by_complexity.png` | Mean CBS per complexity level × model |
| `schema_pass_rate.png` | Schema validation pass rate per model |
| `structural_fidelity.png` | Mean structural fidelity per model (structure task only) |

---

## Reproducibility

- The pipeline resets all per-model state inside each model loop so no run leaks parsed output or validation state into the next.
- Invalid LLM output is never replaced with annotations during live runs.
- When `USE_LLM=0`, annotated data is used as a dry-run baseline so evaluation, logging, and all artifact generation can be tested without model access.
- Every result file is fully overwritten on each run — no stale data accumulates.

---

## Running the Pipeline

Install dependencies:

```bash
uv sync
```

Dry run (uses annotated data as baseline, no LLM calls):

```bash
uv run main.py
```

Live run with all configured models:

```bash
USE_LLM=1 uv run main.py
```

---

## Adding a New Prompt Strategy

1. Open `prompts/structure_prompts.json` or `prompts/business_prompts.json`.
2. Add a new key under `"strategies"` with `{program}` and `{code}` placeholders.
3. Run the pipeline — the strategy is discovered automatically with no code change.

---

## Adding a New Model

1. Open `experiments/constants.py` and add or uncomment a model family.
2. Add the family key to `LLM_Factory.get_AllModels()` in `pipeline/llm_factory.py`.

---

## Repository Layout

```text
assets/raw/
  COBOL Program/          Source COBOL programs used in evaluation
  Annotated data/         Structure ground truth + complexity labels (JSON)
  Business Logic/         Business rule ground truth (JSON)
evaluation/
  evaluation_structure.py Structure matching and structural fidelity computation
  evaluation_business.py  Business rule matching and avg semantic computation
experiments/
  constants.py            Model and path configuration
  pipeline_logger.py      Unified console + file logger
  experiments_log.py      Lightweight JSONL run log
  results/                All output artifacts
    graphs/               Benchmark visualisation charts
pipeline/
  load_data.py            COBOL and annotation file loaders (reads complexity labels)
  llm_factory.py          OpenRouter model instantiation
  llm_call.py             LLM invocation with retry and JSON extraction
  evaluation.py           EvaluationResult — CBS computation, complexity field
  result_reporter.py      JSON, CSV, summary writers; orchestrates extended outputs
  reporting_tables.py     Aggregated CSV table generation (raw, agg, task, complexity)
  graphs.py               Seven matplotlib benchmark charts
  analysis.py             analysis_summary.json and .txt generation
prompts/
  structure_prompts.json  Prompt templates for structure extraction
  business_prompts.json   Prompt templates for business rule extraction
schema/
  program_structure.py    Pydantic output schema for structure task
  business_logic.py       Pydantic output schema for business task
main.py                   Experiment entry point
```

---

## Thesis Evaluation Guidance

| Chapter | Source |
|---------|--------|
| Experimental Setup | Experiment matrix above; model IDs and hyperparameters in `experiments/constants.py` |
| Metrics | CBS formula and metric definitions table in this README |
| Results | `aggregated_results.csv` for model-level tables; `task_results.csv` for task comparison; `complexity_results.csv` for complexity analysis |
| Analysis | `analysis_summary.txt` for best-performer discussion |
| Graphs | All seven charts in `experiments/results/graphs/` (150 dpi, ready to include) |
| Appendix | `analysis_summary.txt` and prompt templates from `prompts/` |
