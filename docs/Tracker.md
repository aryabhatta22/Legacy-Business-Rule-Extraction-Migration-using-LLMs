# Thesis / Project Tracker

Last updated: 2026-07-13.

Related docs: `docs/Implementation_Requirements.md` (detailed task specs T1–T8),
`docs/Execution_Status.md` (session-by-session log of what actually landed and why).
This tracker is the summary view; those two hold the detail.

## Pending tasks (priority order)

| # | Task | Problem | Needs | Status |
|---|------|---------|-------|--------|
| 1 | Apply annotation-quality tweaks found 2026-07-13 (rename ~8 structure names to source spellings; retype `IDENTIFICATION` to `METADATA`; decide on `PROGRAM_METADATA` comment-block entry) | P11 | User decision, then ~1h edits | ❌ Open — full list in `docs/Execution_Status.md` 2026-07-13 section |
| 2 | Full live run — the 160-combination matrix has never been captured (only 16 OPEN_AI × VSCBEX01 runs with an old prompt set exist, archived) | P2 | User go-ahead (API cost); smoke-test first with `PROGRAMS=VSCBEX01 USE_LLM=1` | ❌ Open — everything below needs this data |
| 3 | Calibrate the `0.5` similarity thresholds against labeled pairs; document in `docs/threshold_calibration.md` | P3 | Live-run data (#2) + user labels 30–50 pairs | ❌ Open |
| 4 | Manual evaluator validation — user reviews 20–50 evaluated samples, record agreement rate | P8 | Live-run data (#2) + sampling/export helper script + user review time | ❌ Open |
| 5 | Sub-classify `hallucinated` items (duplicate / split / merged) and add per-model error-type reporting | P4, P9 | Valid data (#2); purely additive code | ❌ Open |
| 6 | Semantic (embedding) similarity to replace/augment token overlap | P6, P7 | User approval — adds a dependency, changes reproducibility | ⏸️ Skipped by user 2026-07-11; re-raise next iteration |
| 7 | Thesis writing: methodology positioning vs prior benchmarks, corrected-evaluator description, calibrated thresholds | P10 | #1–#4 done | ❌ Open (writing task, not repo code) |

Dependency chain in short: **#1 → #2 → (#3, #4, #5) → #7**. #6 is optional and
orthogonal but affects #3 if adopted (thresholds must be recalibrated).

Note for #2/#3: the archived live records embed the OLD ground truth (pre-2026-07-13
re-annotation) inside each record, and `scripts/re_evaluate.py` re-scores against that
stored copy. They cannot be re-scored against the new annotations without recalling the
LLMs — one more reason the fresh full run is the real unblock.

## Pending tasks explained (plain language)

Background for all of them: the benchmark works like grading an exam. The AI models
take the exam (read a COBOL program, list its building blocks and business rules), and
an automatic grader compares their answers against an **answer key** we wrote by hand
(the "annotations" / "ground truth"). Every problem below is about either the answer
key, the grader, or the exam results.

**#1 — Fix small mistakes in the answer key.**
The grader gives full marks only when the model's wording is close enough to the answer
key's wording. In a few places our answer key uses internal shorthand instead of the
names that actually appear in the COBOL source — for example the key says
`INSERT_RECORD` while the program itself calls that block `2100-Insert-CUSTFile`. A
model that answers with the real name from the source (the *better* answer) would be
marked only half-right. There are also two entries where the key's category label
doesn't match what any model would reasonably say, and one entry that covers a comment
block models are never asked to report. If we don't fix these, every model loses the
same few points unfairly, and the final rankings are slightly distorted for no good
reason. The fix is cheap: rename/re-label a handful of answer-key entries before we
spend money on the real exam.

**#2 — Actually run the full experiment.**
The thesis promises a comparison of 4 models × 4 prompt styles × 2 tasks × 5 programs
= 160 test runs. That full exam has never actually been sat: only 16 runs exist, from
one model on one program, taken with an outdated exam paper and graded with a grader
that had a counting bug. Until the full run happens, there are simply no results to
analyze — every task below is waiting on this data. It costs real API money, which is
why it needs an explicit go-ahead and a cheap one-program smoke test first.

**#3 — Justify the pass mark.**
When the grader compares a model's answer to the answer key, it computes a similarity
score between 0 and 1 and calls the answer "correct" if the score is at least 0.5.
That 0.5 was picked by gut feeling, not evidence. In a thesis defense, "why 0.5?" is
an easy attack. The fix: take real graded answers, have a human label which ones are
genuinely right, and check which cutoff best agrees with the human labels — then
document that process. This can't be automated because the human judgment *is* the
evidence.

**#4 — Prove the grader itself can be trusted.**
Everything the thesis reports is produced by our automatic grader, but nobody has ever
checked whether the grader agrees with a human marking the same answers. A reviewer can
ask: "your grader says model X is best — how do you know your grader is right?" The
fix: a human reviews 20–50 graded answers, and we report the agreement rate between
human and grader. High agreement = the grader is credible evidence.

**#5 — Say *why* models get things wrong, not just how often.**
Right now, any answer the grader can't match to the answer key lands in one bucket
called "hallucinated" (made up). But that bucket mixes very different mistakes: the
model repeating the same item twice, splitting one rule into two, or merging two rules
into one. These aren't equally bad, and telling them apart makes the thesis discussion
chapter much stronger ("model X mostly duplicates, model Y invents"). The fix is a
post-processing step that sorts the bucket into sub-categories and reports them
per model.

**#6 — Smarter similarity scoring (currently on hold).**
The grader measures similarity by counting shared words. That means "customer record
is written to the indexed file" and "the system saves client data" score as *different*
even though they mean the same thing — so models that paraphrase well get punished.
The fix is to use an embedding model (a small AI that scores *meaning* similarity
rather than word overlap). Deliberately postponed: it adds a new dependency and
changes reproducibility of results, so it needs an explicit decision.

**#7 — Update the thesis text.**
Not a code task. Once #1–#4 are done, the methodology and results chapters must
describe the *corrected* grader, the *calibrated* pass mark, and position the benchmark
against prior published work — otherwise the text describes a setup that no longer
exists in the repo.

## Resolved

| Problem | Was | Resolution |
|---------|-----|------------|
| P1 🔴 Structure evaluator never produced `correct` | Annotations had no `name` field → name score always 0.0 → every match `partial` | ✅ 2026-07-13 — user re-annotated all 5 programs (names + richer business schema); old data in `v2/` subfolders. Dry-run self-comparison now `correct=N, partial=0` on every program |
| P5 🟠 Raw LLM response not stored | Only the parsed dict was kept; extraction failures undebuggable after the run | ✅ 2026-07-12 — `raw_response` threaded into `results.json` for all future runs (no backfill for past runs) |
| P2 (tooling half) 🔴 Re-evaluation capability | Couldn't re-score saved outputs without recalling LLMs | ✅ 2026-07-12 — `scripts/re_evaluate.py` (no LLM calls, rewrites all artifacts, preserves timestamps). Data half stays pending (#2 above) |
| Dev cost control | User moved `.cbl` files out of the data dir to limit test runs | ✅ 2026-07-12 — `PROGRAMS` env filter in `main.py` |
| README strategy-name mismatch | README documented `direct/few_shot/cot/modular`; code uses `naive/structured/few_shot/cot_hidden` | ✅ 2026-07-13 — README updated to actual strategy names |

## Open problem register (detail)

| ID | Level | Problem | Mitigation |
|----|-------|---------|------------|
| P2 | 🔴 Critical | No trustworthy benchmark data exists: the full matrix was never run, and the 16 archived live records used an old prompt set, an old double-counting evaluator, and now-superseded ground truth | Fresh `USE_LLM=1` full run after #1; treat the archive as historical evidence only |
| P3 | 🟠 High | Similarity thresholds (`0.5` in both evaluators) are uncalibrated constants — thesis-defense risk. New annotation names make it tighter: division names score exactly 0.50 vs source spellings, so the threshold cannot be raised without renaming them | Label pairs from live data, pick separating threshold, document method |
| P4 | 🟠 High | All unmatched predictions bucket as `hallucinated`; no duplicate/split/merged distinction | Post-processing sub-classification + reporting extension |
| P6 | 🟡 Medium | Structure name matching is plain token overlap — fragile to paraphrase | Semantic similarity (with P7) once approved |
| P7 | 🟡 Medium | Business rule matching is pure token Jaccard — misses paraphrases, underestimates models | Embedding similarity with calibrated threshold; keep Jaccard as tie-breaker |
| P8 | 🟡 Medium | Evaluator never validated against human judgment | Manual review of 20–50 samples, report agreement rate |
| P9 | 🟢 Low | Reports are summary-level only | Per-model breakdowns + error types once P4 lands |
| P10 | 🟢 Low | Methodology not positioned against prior benchmark literature | Writing task, after evaluator fixes are final |
| P11 | 🟢 Low (new 2026-07-13) | Annotation names are id-copies, not source spellings; `IDENTIFICATION` typed `DECLARATION` (type-incompatible with what models emit); `PROGRAM_METADATA` covers a comment block models are never asked for | Rename/retype per `docs/Execution_Status.md` 2026-07-13 list — cheap, do before spending API credit |

## Component status

| Component | Status |
|-----------|--------|
| Dataset, prompts, LLM integration, JSON validation, extraction pipelines | ✅ Complete |
| COBOL annotation (structure + business ground truth) | ✅ Re-annotated 2026-07-13; minor quality tweaks pending (P11) |
| Benchmark framework (CBS, fidelity, avg_semantic, schema pass rate) | ✅ Implemented |
| Evaluation framework | ✅ Structure evaluator fixed (P1); token-based similarity remains (P6/P7) |
| Experiment repository | ✅ Parsed + raw output, ground truth, details, metrics all stored per run |
| Benchmark data | ❌ Full 160-run matrix never captured — blocking item |
| Threshold calibration / statistical analysis | ❌ Not started (needs data) |
| Thesis writing | ⚠️ In progress (~65%) |
