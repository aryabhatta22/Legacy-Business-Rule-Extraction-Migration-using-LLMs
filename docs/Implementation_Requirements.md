# Implementation Requirements — Evaluation Framework Fixes

Handoff doc for a fresh Claude Code session. Read this fully before touching code —
it has verified root causes, not guesses. Cross-reference `docs/Tracker.md` for full
problem register and `docs/Temp/Another_repo_evaluation_summary.md` for external context
(lower priority, background only).

## Primary goal

Thesis benchmark results must be trustworthy. Structure-task evaluation currently
produces `correct=0` for every run regardless of model quality — that's the #1 blocker
**for the structure task specifically**. Everything else here is secondary and ordered
by dependency + effort/impact.

## Decisions made 2026-07-11 (user)

- **T1 deferred, not skipped.** User chose to hold off implementing either T1 option
  this iteration rather than pick A or B now. Both options remain documented below —
  pick one when resuming. Tracked as pending in `docs/Tracker.md` (P1).
- **T5 (embedding similarity) skipped.** Keep token Jaccard/overlap. No new dependency
  added this iteration.

These two deferrals change which parts of T2/T4/T6 can run now — see the "blocked by
T1" notes inside each task below. **Business-task work is NOT blocked** — only T1 is
a real dependency, and it only affects the structure task.

## Ground truth already verified (don't re-derive, just confirm still true before coding)

- `evaluation/evaluation_structure.py::_normalize_structure` (line ~65) already maps
  `item.get("name", "")` correctly — the field-key mapping is NOT broken.
- `assets/raw/Annotated data/*.json` structures have **no `name` field** — only `id`,
  `type`, `lines`. So annotated name is always `""`, token overlap vs `""` is always
  `0.0`, so every structure match falls to `partial` (threshold is `>= 0.5` in
  `evaluation_structure.py` line ~194). Verified via dry-run self-comparison of VSCBEX01:
  `correct=0, partial=11` (should be `correct=11` if names matched, since it's comparing
  the annotation against itself).
- `pyproject.toml` / `uv.lock` have no embedding/semantic-similarity library. Both
  evaluators use token Jaccard/overlap only.
- `results.json` (via `pipeline/evaluation.py::EvaluationResult`) already stores parsed
  `llm_output`, `ground_truth`, `evaluation_details`, `metrics` per run. Only the raw
  pre-parse LLM response text is missing.
- Business evaluator self-comparison already works correctly (`correct=10/10` on
  VSCBEX01 dry run) — business task is NOT broken the way structure task is.

## Task list, in required execution order

### T1 — Fix structure evaluator name matching (Critical — DEFERRED, pending user decision)

**Status: pending, not started.** User deferred this in the 2026-07-11 planning session
rather than pick an option. Do not implement without asking the user to pick Option A
or B first — this is still a real tradeoff, not a default-pick situation.

Problem: `assets/raw/Annotated data/*.json` structures lack a `name` field, so
`evaluate_structure_base` in `evaluation/evaluation_structure.py` never scores a
`correct` match (`_token_overlap_ratio` against empty string == `0.0` always).

Pick ONE of these two approaches — decide with the user before implementing, don't
silently choose:

- **Option A (preferred): add `name` to every structure entry** in all 5 files under
  `assets/raw/Annotated data/*.json` (VSCBEX01–05). Requires reading each COBOL source
  under `assets/raw/COBOL Program/*.cbl` and writing a human-reasonable name per
  structure `id`/`type`/`lines` (e.g. paragraph/section names as they appear in source).
  Manual, ~11-20 structures per file × 5 files. More defensible for thesis (ground truth
  should have names, matches what business rules already do).
- **Option B (faster patch): change the matcher** in
  `evaluation/evaluation_structure.py::evaluate_structure_base` so that when
  `annotated_item.get("name")` is empty/missing, name scoring is skipped and the match
  is scored `correct` on type+line-overlap alone (don't force it to `partial`). Faster,
  but weakens the "correct" signal for structure task — no name-quality check ever
  happens. Flag this tradeoff explicitly in the thesis methodology section if chosen.

Acceptance check: re-run dry-run (`uv run main.py`, `USE_LLM=0`) and confirm structure
task self-comparison on VSCBEX01 yields `correct=11, partial=0` (or close to it,
depending on real annotation quality) instead of `correct=0, partial=11`.

### T2 — Re-evaluate all saved outputs with fixed evaluator (Critical for business task; structure task blocked by T1)

No LLM recall needed — `results.json` already has `llm_output` per run. Write a small
script (new file, e.g. `scripts/re_evaluate.py` or reuse `main.py` in `USE_LLM=0`/offline
mode) that:
1. Loads existing `experiments/results/results.json`.
2. Re-runs `evaluate_structure()` / `evaluate_business()` per record using the already-
   stored `llm_output` and `ground_truth`.
3. Rewrites `results.json`, `results_summary.csv`, `summary.json` and calls
   `pipeline/reporting_tables.py` + `pipeline/graphs.py` + `pipeline/analysis.py` to
   regenerate aggregated tables and charts.

Constraint: must not call any LLM. Must not corrupt `experiments/log.jsonl` format
consumers expect.

**Blocked-by-T1 note:** business-task rows can be re-evaluated and trusted now — the
business evaluator is not affected by T1. Structure-task rows can technically be
re-evaluated too, but the output is still `correct=0` for every run until T1 lands —
re-running now would just reproduce the same broken numbers with a fresh timestamp.
Recommend: run T2 scoped to business task only for now, or run both but clearly label
structure-task output as provisional/known-broken in any report that uses it.

### T3 — Store raw LLM response text (High, independent — can run parallel to T1/T2)

Correction to earlier draft: `pipeline/llm_call.py::LLMCaller.call()` (line ~127)
already returns `"raw": last_raw` in its response dict — the raw pre-parse agent output
IS captured, it's just discarded by `main.py`, which only reads `response.get("parsed")`.
So this is a threading task, not a capture task:
`main.py` (`response.get("raw")`) → new param on `build_evaluation_result()` in
`pipeline/evaluation.py` → new field on `EvaluationResult` → included in
`EvaluationResult.to_dict()` → written to `results.json`.
Note: `raw` may be a LangChain message object, not a plain string — stringify/serialize
it before storing (JSON dump already uses `default=str` in `ResultReporter.save_json()`,
so this mostly works out of the box, but confirm the stored value is actually useful for
debugging, not just a repr). Only affects future runs — no backfill possible for
already-discarded raw text from past runs.

### T4 — Calibrate similarity thresholds (High for business task; structure task blocked by T1)

Currently both evaluators use a hardcoded `0.5` threshold
(`evaluation_structure.py` line ~194, `evaluation_business.py` line ~130). Needs:
1. Sample 30-50 matched pairs (mix of correct/partial/wrong) from re-evaluated results.
2. Human labels the pairs (this step needs the user, not automatable by Claude).
3. Compute similarity scores for labeled pairs, pick threshold that best separates
   correct vs partial/wrong groups.
4. Update the `0.5` constants with the calibrated value(s) and document the calibration
   method/data in a new `docs/threshold_calibration.md` (or thesis appendix).

This task requires user input mid-way (manual labeling) — can't be fully automated in
one sitting. Flag this to the user when starting T4.

**Blocked-by-T1 note:** calibrating the structure-task threshold against current data is
meaningless — every structure match is `partial` regardless of quality, so there's no
real correct/partial/wrong spread to calibrate against. Business-task calibration can
proceed independently now.

### T5 — SKIPPED per user decision, 2026-07-11

User chose to keep token Jaccard/overlap and not add an embedding dependency this
iteration. Original proposal preserved here for the next iteration: replace/augment
token Jaccard (`evaluation_business.py::_token_jaccard_similarity`) and token overlap
(`evaluation_structure.py::_token_overlap_ratio`) with embedding-based cosine similarity
via a new dependency (e.g. `sentence-transformers`). Re-raise with the user before
picking this up again — it changes reproducibility (model cache/internet on first run)
and adds runtime cost across all 160 combinations.

### T6 — Manual evaluator validation (Medium for business task; structure task blocked by T1)

User manually reviews 20-50 evaluated samples (correct/partial/hallucinated labels from
the evaluator) and records agreement rate vs their own judgment. Needs a small script or
spreadsheet export helper (new file) to sample and format N results from `results.json`
for review. Requires user's manual review time — not automatable.

**Blocked-by-T1 note:** validating the structure evaluator's judgment now would just
confirm "it always says partial," which isn't useful signal. Scope this to business-task
samples until T1 lands.

### T7 — Error classification / richer reporting (Low priority — do last)

Extend `evaluate_business` / `evaluate_structure` (or a post-processing pass) to
sub-classify `hallucinated` items into duplicate / split / merged-rule categories.
Extend `pipeline/reporting_tables.py` / `pipeline/graphs.py` with per-model error-type
breakdowns. Purely additive, no dependency on T1-T6 except wanting valid data first.

### T8 — Thesis writing updates (Low priority, final step)

Update methodology/results/discussion chapters to reflect the corrected evaluator,
calibrated thresholds, and semantic similarity approach. Not a code task — flag as
writing work, not something to execute in this repo.

## Non-goals (do not change without explicit user ask)

- COBOL dataset, prompt strategies, LLM model list, JSON schemas, CBS formula weights —
  all confirmed working, out of scope per `docs/Temp/Another_repo_evaluation_summary.md`
  and `docs/Tracker.md`.
- Don't rerun LLMs (`USE_LLM=1`) unless the user explicitly asks — costs money, calls
  external API.

## Before starting any task

1. Re-read `docs/Tracker.md` for current problem register / status.
2. Confirm with user which T1 option (A or B) to implement — this is a real tradeoff,
   not a default-pick situation.
3. Follow repo's existing reproducibility invariants (see root `CLAUDE.md`): reset
   per-run state, never let live-run failures fall back to annotations, fully overwrite
   `experiments/results/` outputs, reset `experiments/log.jsonl` at run start.
