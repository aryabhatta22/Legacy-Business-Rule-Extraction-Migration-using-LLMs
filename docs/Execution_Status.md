# Execution Status — Evaluation Framework Fixes

Running log of what has actually been implemented from `docs/Implementation_Requirements.md`.
Update this file whenever a task lands so a fresh session can resume without re-deriving state.

Last updated: 2026-07-19.

## 2026-07-19 — Fix batch implemented (user-approved plan)

All changes below were approved by the user before implementation.

1. **Annotations (change note):** dropped the `PROGRAM_METADATA` comment-header entry
   from all 5 structure files (models are never asked for comment blocks; it was a
   guaranteed miss) and retyped `ENVIRONMENT_DIV` from `FILE_CONTROL` (unmatchable —
   not in the type map or schema) to `CONFIGURATION`. Structure counts are now
   10/8/8/10/10.
2. **Numbered source lines in prompts:** `main.py::_cobol_code_from_lines` now
   prefixes every line with its absolute number (`"77: 1000-Begin-Job."`). This is a
   deliberate benchmark-design change (user-approved): ground truth and the evaluators
   reference absolute line numbers, so models must see them — without this the
   line-overlap gate made the tasks unwinnable. Applies identically to all strategies,
   so strategy comparison stays internally fair. Thesis methodology must state it.
3. **Prompt/schema alignment:** the JSON examples in `prompts/*.json` now show the
   exact fields the Pydantic schemas enforce (`structure_id`/`structure_type`/
   `line_range`/`description`/`parent_id`; `rule_id`/`rule_category`/`domain`/
   `evidence{source_structures,source_lines}`/`confidence`/`assumptions`), including
   allowed enum values. Strategy character (naive/structured/few_shot/cot_hidden)
   unchanged; `cot_hidden` still has no `{program}` placeholder, as before.
4. **`error_message` stored per run** (exception or pydantic validation error text
   from `LLMCaller`) in `results.json` — failed runs are now diagnosable.
   `scripts/re_evaluate.py` preserves it.
5. **Two new metrics (change note):** `precision_lenient` / `recall_lenient`
   (partial matches earn half credit; CBS unchanged) and `avg_line_iou` (mean
   intersection-over-union of matched line ranges — measures location precision,
   which the 19-Jul analysis showed is the weakest link). Added to `results.json`,
   `results_summary.csv`, and all aggregated tables.

Verification: full dry run (5 programs, 40 records) — self-comparison perfect
(`correct=N, partial=0` everywhere), new metric fields present in JSON + both CSVs,
`error_message=None` on dry runs as expected.

**Live smoke test (`PROGRAMS=VSCBEX01,VSCBEX02 USE_LLM=1`) outcome:** first attempt
completed 31/64 runs (evidence preserved in `experiments/log.jsonl` from that run),
then hung ~1h on a QWEN call — root cause: no request timeout on `ChatOpenRouter`.
Fixed (default `timeout` in `pipeline/llm_factory.py`, raised to 300s after a 120s
retry showed ~50% call timeouts across ALL model families during a degraded
OpenRouter window). Also added a hard abort in `main.py` when `USE_LLM=1` finds no
configured models (missing `OPENROUTER_API_KEY` previously produced a silent empty
"successful" run; note `.env` is NOT auto-loaded by the pipeline). The 31 healthy
runs confirmed: all 4 model families schema-valid (Gemma and LLaMA included — both
broken before), business matching works with numbered lines (up to 9/10 rules
matched vs ~0/10 before), `avg_line_iou` 0.13–0.58, business `correct` still 0
pending threshold calibration (expected). **User chose (19 Jul) to skip a smoke-test
rerun and go straight to the full 160-run matrix in a healthy provider window** —
that full run doubles as the final artifact-generation verification on live data.

## 2026-07-19 — Analysis of "business rules failing" + LLM-reported bugs (no fixes yet)

Analyzed `assets/temp/experiment results Befor 19 Jul` (24 records: gpt-4.1-mini,
llama-3.1-8b, qwen-2.5-72b × VSCBEX01 × 4 strategies × 2 tasks; 22/24 schema-valid).

**Root cause of business-task failure — line numbers, not the threshold.** The prompt
embeds COBOL source with NO line numbers, but the matcher requires positive
source-line overlap as a hard gate. Models must guess absolute line numbers and can't:
ground truth rules sit at lines 77–136; gpt reported 20–77; qwen reported lines past
the end of the 136-line file (158–166). Most rules therefore never match at all
(`missing`+`hallucinated`), and the few that do match score 0.06–0.20 Jaccard →
`correct=0` everywhere. Fix direction: number the source lines in the prompt
(`1: IDENTIFICATION DIVISION.` …) so line grounding is possible, then revisit
similarity threshold via calibration (T4).

**Verdict on the four LLM-reported bugs:**
- Bug 1 (`create_agent` deprecated/breaks) — **false**. It's the current LangChain 1.x
  API; imports fine on installed 1.2.3, and qwen/llama produced schema-valid output in
  20/24 runs. The 2 llama `error` rows are pre-response exceptions (raw_response None,
  exception text not stored — worth adding).
- Bug 2 (0.5 threshold makes business correct=0) — **symptom real, diagnosis
  incomplete**: threshold only matters after a line-overlap match; the line gate is the
  real killer (above). Don't lower 0.5 ad hoc — that's the T4 calibration task.
- Bug 3 (structure prompts show `start_line`/`end_line` etc., schema wants
  `line_range`/`structure_id`/…) — **true mismatch**, but "every model fails
  validation" is false: `ProviderStrategy` enforces the schema server-side, so outputs
  validate anyway. Harm is content confusion, not validation failure.
- Bug 4 (business prompts show only `rule_statement`/`source_lines` vs full schema) —
  **true mismatch**, same caveat as Bug 3.

**New annotations (v3 moved, fresh data in place) checked:** P11 tweaks applied
(source-spelling names, `IDENTIFICATION` retyped `METADATA`). One new defect:
`ENVIRONMENT_DIV` is typed `FILE_CONTROL` in all 5 files — `FILE_CONTROL` is not in
`STRUCTURE_TYPE_MAP` and not emittable by the schema, so that structure is permanently
unmatchable (systematic `missing` ×5). Retype (e.g. `CONFIGURATION`) or extend the map.

**Testing protocol going forward (user request):** test runs use at least two programs
(`PROGRAMS=VSCBEX01,VSCBEX02`), and every test run ends with verification of the
generated metric files, not just "pipeline finished".

## 2026-07-13 — T1 landed (user re-annotated), verified

User rewrote all annotations (structure + business); previous versions moved to
`Annotated data/v2/` and `Business Logic/v2/`. Verification results:

- **Structure**: every entry has non-empty `name`, `id`, `type`, `lines`; all line
  ranges within file bounds; `complexity.level` present (load_data reads it fine).
- **Business**: new richer rule schema (precondition/action/postcondition, variables,
  confidence…). Evaluator-compatible — it reads `rules[].rule_id`,
  `natural_language_rule`, `source_lines`, all present. 42 rules total (10/7/8/9/8).
- **T1 acceptance check PASSED**: full dry-run self-comparison now gives
  `correct=N, partial=0, missing=0, hallucinated=0` for every program on both tasks
  (VSCBEX01 structure: correct=11 — previously correct=0). Global dry-run CBS=1.0.
- P1 is RESOLVED; P2/P3/P8 are unblocked for the structure task.

Known annotation-quality risks for LIVE runs (names are id-copies, not source
spellings; simulated against source headings with the real `_token_overlap_ratio`):

1. `INSERT_RECORD`/`UPDATE_RECORD`/`DELETE_RECORD`/`READ_RANDOM`/`REWRITE_CUSTFILE`
   score 0.25–0.33 vs their source names (`2100-Insert-CUSTFile`, `5000-Read-CUSTFile`,
   `6000-Re-Write-CUSTFile`…) → a perfect model gets `partial`, not `correct`, on
   ~1–3 structures per file. Fix: set annotation `name` to the source spelling.
2. `IDENTIFICATION` is typed `DECLARATION`; LLMs will emit `DIVISION`, whose
   compatibility set is {METADATA, CONFIGURATION, DATA} → systematic miss+hallucination
   on all 5 files. Fix: retype to `METADATA` (or extend the map — methodology change).
3. `PROGRAM_METADATA` covers the comment header (lines 1–22); prompts never ask for
   comment blocks → likely systematic `missing` for every model. Decide: drop the entry
   or accept the recall penalty knowingly.
4. `PROCESS_LOOP` type `LOOP` only matches if the model emits type `LOOP` for the
   `2000-Process` paragraph; a model emitting `PARAGRAPH` is incompatible (PARAGRAPH
   set lacks LOOP). Model-dependent risk; watch it in the first live run.
5. Divisions sit exactly at the 0.5 threshold (`ENVIRONMENT_DIV` vs
   "ENVIRONMENT DIVISION" = 0.50) — passes today, but T4 calibration must not raise
   the threshold above 0.5 without renaming these.

## Done (2026-07-12 session)

### PROGRAMS filter (dev cost control — replaces manual file moving)

`main.py` now reads a `PROGRAMS` env var (comma-separated, e.g. `PROGRAMS=VSCBEX01`)
and filters loaded programs before the run loop. Empty/unset = all programs. Use this
instead of moving `.cbl` files out of `assets/raw/COBOL Program/` for cheap test runs:

```bash
PROGRAMS=VSCBEX01 USE_LLM=1 uv run main.py   # live run, one program only
```

All 5 `.cbl` files are back in `assets/raw/COBOL Program/`. Verified: no filter loads
all 5 programs; `PROGRAMS=VSCBEX01` dry run processes only VSCBEX01.

### Live-run archive

`experiments/results/` is fully overwritten every run, and the only live-run
(`USE_LLM=1`) records ever produced — 16 records, OPEN_AI family, VSCBEX01, old
8-strategy prompt set, 2 tasks — existed only in git history. They are now preserved
at `experiments/archive/results_live_openai_vscbex01.json` (see `experiments/archive/README.md`).

### T3 — raw LLM response stored (DONE)

`main.py::_serialize_raw_response()` extracts the final message text from
`LLMCaller.call()`'s `raw` return; threaded through `_record_result` →
`build_evaluation_result(raw_response=...)` → `EvaluationResult.raw_response` →
`to_dict()` → `results.json`. `None` on dry runs and pre-response failures. Verified
present in dry-run output. Backfill impossible for past runs (raw was discarded).

### T2 — re-evaluation script (DONE)

`scripts/re_evaluate.py`: re-runs `evaluate_structure`/`evaluate_business` on every
record of an existing `results.json` using stored `llm_output` + `ground_truth`,
rewrites all artifacts via `ResultReporter` + `generate_extended_outputs()`. No LLM
calls; does not touch `experiments/log.jsonl`; logs to `experiments/re_evaluate_log.txt`
(not `run_log.txt`); preserves original `timestamp`, adds `re_evaluated_at`.

```bash
uv run python scripts/re_evaluate.py --input experiments/archive/results_live_openai_vscbex01.json --results-dir experiments/results
```

Verified against the 16 archived records: runs clean, business rows re-scored.

## Discoveries this session (change earlier assumptions)

1. **Old evaluator double-counted.** Archived records' stored metrics are ~2× the
   counts the current evaluator produces on identical `llm_output`/`ground_truth`
   (e.g. business `missing 12 → 6`, `total_ground_truth` 20 vs real 10). Any numbers
   from those old runs must be re-derived via `scripts/re_evaluate.py`, never quoted
   as stored.
2. **P1 "correct always 0" applies to the CURRENT annotations only.** The archived
   records embed an older ground truth that HAS `name` + `description` per structure —
   re-evaluating them yields nonzero structure `correct` (3–11). The names were lost
   when annotations were revised.
3. **`assets/raw/Annotated data/v1/*.json` contains those older annotations with
   `name` + `description` for every structure.** This makes T1 Option A much cheaper
   than the requirements doc estimates: carry `name` over by matching `id` (most ids
   overlap with the current files), then hand-write names only for the few
   current-only ids (`PROGRAM_METADATA`, `DATA_DIV`, `READ_INPUT`, etc.). Note the
   structure sets differ (v1 has 11–14 entries incl. `WORKING_STORAGE`/`ERROR_HANDLING`;
   current has 9–11 with different line ranges), so it's a merge, not a copy.
4. **Archived live runs used an old 8-strategy prompt set** (`naive_1`, `naive_2`,
   `structured_1/2`, `cot_hidden_1/2`, `structure_aware_1/2`) — not the current 4
   (`naive`, `structured`, `few_shot`, `cot_hidden`). Treat that archive as historical
   evidence, not thesis-comparable data; final numbers need a fresh `USE_LLM=1` run.

## Still open (in dependency order)

- **T1 (P1)** — ✅ DONE 2026-07-13 (user re-annotated, Option A). Residual: the five
  annotation-quality tweaks listed above, pending user decision.
- **Full live run** — the 160-combination matrix has never been captured. Needed for
  thesis results; costs API credit; use `PROGRAMS` filter for smoke tests first.
- **T4 (P3)** — threshold calibration; needs user labeling; business task only until T1.
  Current 8 archived business rows are likely too few/homogeneous — calibrate after a
  fuller live run.
- **T6 (P8)** — manual evaluator validation; needs a sampling/export helper + user
  review; business task only until T1.
- **T7 (P4/P9)** — hallucination sub-classification, richer reporting. Do last.
- **T8 (P10)** — thesis writing; also reconcile README strategy names
  (`direct/few_shot/cot/modular`) with actual (`naive/structured/few_shot/cot_hidden`).
