# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A reproducible benchmarking framework for evaluating LLMs on COBOL legacy-modernization
tasks (structure extraction and business-rule extraction). It runs 160 experiment
combinations: 4 models × 4 prompt strategies × 2 tasks × 5 COBOL programs, all models
accessed through OpenRouter via a single `OPENROUTER_API_KEY`. This is thesis/research
code — `main.py` is the single entry point that runs the full matrix each time.

## Commands

```bash
uv sync                    # install dependencies
uv run main.py              # dry run: uses annotated data as baseline, no LLM calls
USE_LLM=1 uv run main.py    # live run: calls all configured models via OpenRouter
PROGRAMS=VSCBEX01 USE_LLM=1 uv run main.py   # live run limited to listed programs (comma-separated)
uv run python scripts/re_evaluate.py         # re-score a saved results.json without any LLM calls
```

There is no test suite, linter config, or CI in this repo. Runtime switches (env vars):
`USE_LLM` (default `0`) — when unset/`0`, annotated ground truth is substituted for LLM
output so the full pipeline (evaluation, logging, artifact generation) can be exercised
without network access or cost. `PROGRAMS` (default empty = all programs) —
comma-separated program names, used to keep dev/test live runs cheap.

`experiments/results/` is overwritten every run; one-off snapshots worth keeping live in
`experiments/archive/` (see its README). `docs/Execution_Status.md` tracks which fixes
from `docs/Implementation_Requirements.md` have landed.

## Architecture

The pipeline is a straight loop, not a framework — `main.py` is the place to start
reading. For each `program × {structure, business} × strategy × model`:

1. **`pipeline/load_data.py`** loads COBOL source + annotations (structure ground truth,
   business rule ground truth, complexity label) per program from `assets/raw/`.
2. Prompt templates come from `prompts/structure_prompts.json` /
   `prompts/business_prompts.json` under a `"strategies"` key — adding a new strategy is
   just adding a JSON key with `{program}`/`{code}` placeholders, no code change needed.
   `main.py::_fill_prompt` uses plain `str.replace`, not `str.format`, because templates
   embed literal JSON examples that would otherwise be parsed as placeholders.
3. **`pipeline/llm_factory.py`** builds one `ChatOpenRouter` instance per model family
   defined in **`experiments/constants.py::MODEL_CONSTANTS`**. To add a model: add/uncomment
   a family there, then add the family key to `LLM_Factory.get_AllModels()`.
4. **`pipeline/llm_call.py`** (`LLMCaller`) invokes the model with retries and extracts
   JSON via a single deterministic strategy (strip code fences → first `{` to last `}` →
   `json.loads`) — intentionally not a multi-strategy fallback, so extraction failures
   are visible rather than silently patched over.
5. Output is validated against the task's Pydantic schema (`schema/program_structure.py`
   or `schema/business_logic.py`).
6. **`evaluation/evaluation_structure.py`** / **`evaluation/evaluation_business.py`** match
   inferred output to ground truth and produce `correct`/`partial`/`missing`/`hallucinated`
   classifications feeding precision, recall, completeness, hallucination rate, and
   structural fidelity / avg semantic score.
7. **`pipeline/evaluation.py`** (`build_evaluation_result`) computes the Composite
   Benchmark Score (CBS) — the primary thesis metric — as
   `0.40*Recall + 0.30*Precision + 0.20*(1-Hallucination) + 0.10*Completeness`.
8. **`pipeline/result_reporter.py`** accumulates every run's record and, at the end of
   `main()`, writes JSON/CSV/summary files, then `pipeline/reporting_tables.py` builds
   aggregated tables and `pipeline/graphs.py` renders the seven benchmark charts
   (150 dpi) into `experiments/results/graphs/`. `pipeline/analysis.py` writes the
   best-performer summary (`analysis_summary.json`/`.txt`).

**Reproducibility invariants** (don't break these when editing `main.py`):
- Every per-run variable (`parsed`, `validation_status`, `eval_report`) is reset inside
  the model loop so no state leaks between runs.
- In live runs (`USE_LLM=1`), invalid/failed LLM output must never fall back to
  annotated ground truth — that would silently corrupt metrics. The annotation fallback
  in `_select_inferred_output` only applies when `USE_LLM=0`.
- All files under `experiments/results/` are fully overwritten each run, and
  `experiments/log.jsonl` is reset at the start of each run — no stale data accumulates.

## Logging

`experiments/pipeline_logger.py` is a singleton logger writing to console (with stage
indentation) and `experiments/run_log.txt`. `experiments/experiments_log.py` appends one
JSON-lines record per completed run to `experiments/log.jsonl`. Use `get_logger()` /
`init_logger()`, don't instantiate loggers directly.

## Full metric/file reference

`README.md` documents in detail: the CBS formula and rationale, the structure/business
matching algorithms (including the type-compatibility map and structural fidelity
definition), every output file under `experiments/results/` and what it contains, and
the seven generated graphs. Read it before modifying `evaluation/` or `pipeline/graphs.py`.
