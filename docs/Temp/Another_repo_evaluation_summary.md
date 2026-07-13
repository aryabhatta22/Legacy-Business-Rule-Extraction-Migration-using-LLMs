# **1\. Repository Comparison with Your Thesis**

| Repository | Main Purpose | Similarity to Your Thesis | What You Already Have | What Is Different | What Can You Reuse | Reusability |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **COBOLEval (BloopAI)** | Python → COBOL translation benchmark with compile-and-test evaluation | ⭐⭐☆☆☆ (Low) | Dataset evaluation, reproducible experiments, benchmark execution | Evaluates executable COBOL using compilation and tests, not business-rule extraction | Deterministic evaluation workflow, benchmark organization, experiment reproducibility | **30%** |
| **COBOL-Coder** | COBOL translation benchmark, evaluation scripts, JSONL experiments | ⭐⭐⭐⭐☆ (High) | Multi-model evaluation, benchmark comparison, result logging | Translation rather than rule extraction | JSONL experiment format, evaluation pipeline, benchmark reporting, model comparison tables | **70%** |
| **AgentModernize** | Legacy modernization pipeline with staged evaluation | ⭐⭐⭐⭐⭐ (Very High) | Structure extraction → Business rule extraction pipeline | Produces executable modernization artifacts instead of JSON rules | Gold-standard evaluation philosophy, staged evaluation, benchmark scenarios, evaluation reporting | **80%** |
| **XMainframe** | COBOL datasets (QA, summarization, MCQ) | ⭐⭐☆☆☆ (Low) | COBOL domain knowledge | Different downstream tasks (QA instead of extraction) | Dataset organization, benchmark description, literature support | **20%** |

# **3\. What You Should Reuse**

| Repository | Recommended Reuse | Why |
| ----- | ----- | ----- |
| **COBOLEval** | Experiment workflow and reproducible benchmark execution | Gives your benchmark a more systematic structure |
| **COBOL-Coder** | JSONL experiment storage, evaluation pipeline, benchmark tables | Closely matches your "run model → evaluate → compare" workflow |
| **AgentModernize** | Gold-standard evaluation philosophy, staged evaluation, benchmark scenario organization | Closest conceptual match to your thesis |
| **XMainframe** | Dataset description and literature references | Strengthens related work and benchmark justification |

**No.** In fact, **I would strongly advise against changing the whole pipeline** at this stage of your thesis.

Based on everything I've seen in your project over the past few weeks, your **pipeline is already correct**. The problem is **not the pipeline**—it's primarily the **evaluation layer**.

## **Your Current Pipeline**

COBOL Program  
     │  
     ▼  
Prompt Builder  
     │  
     ▼  
LLM  
     │  
     ▼  
JSON Output  
     │  
     ▼  
Schema Validation  
     │  
     ▼  
Structure Evaluation  
     │  
     ▼  
Business Rule Evaluation  
     │  
     ▼  
CBS  
     │  
     ▼  
Graphs & Tables

This is a perfectly reasonable pipeline for a Master's thesis.

---

# **What I recommend changing**

Instead of changing the pipeline, **change only the evaluation block**.

COBOL Program  
     │  
     ▼  
Prompt Builder  
     │  
     ▼  
LLM  
     │  
     ▼  
JSON Output  
     │  
     ▼  
Schema Validation  
     │  
     ▼  
══════════════════════════════════  
Improved Evaluation  
══════════════════════════════════  
     │  
     ├── Structure Evaluation  
     │      ├─ Type Match  
     │      ├─ Semantic Name Match  
     │      ├─ Line Overlap  
     │      └─ Hierarchy Check  
     │  
     ├── Business Evaluation  
     │      ├─ Semantic Similarity  
     │      ├─ Evidence Match  
     │      └─ Rule Coverage  
     │  
     └── Error Classification  
══════════════════════════════════  
     │  
     ▼  
CBS  
     │  
     ▼  
Graphs & Tables

Everything before and after that stays the same.

---

# **What Changes?**

| Component | Current | After Improvement |
| ----- | ----- | ----- |
| Dataset | ✅ Same | No change |
| COBOL Programs | ✅ Same | No change |
| Prompt Strategies | ✅ Same | No change |
| LLM Models | ✅ Same | No change |
| Annotation Format | ✅ Same | No change |
| JSON Schema | ✅ Same | No change |
| Structure Extraction | ✅ Same | Minor evaluation improvements only |
| Business Rule Extraction | ✅ Same | Minor evaluation improvements only |
| Evaluation Logic | ⚠️ Improve | Yes |
| CBS | ⚠️ Update inputs | Small change |
| Graphs | ⚠️ Regenerate | Yes |

---

Below is the roadmap I would give you **as your thesis supervisor**, ordered by **priority**. This focuses on **fixing the evaluation** while keeping the rest of your thesis intact.

## **Evaluation Improvement Roadmap**

| Step | Priority | Problem ID | Evaluation Component | Current Problem | Recommended Action | Files to Modify | Estimated Effort | Expected Impact | Thesis Impact |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **1** | 🔴 Critical | **EVAL-01** | Structure Evaluator | `structure_name` is not mapped correctly, resulting in empty names and `Correct = 0`. | Update `_normalize_structure()` to support both `structure_name` and `name`. | `evaluation_structure.py` | 15–30 min | ⭐⭐⭐⭐⭐ | Fixes invalid structure evaluation. |
| **2** | 🔴 Critical | **EVAL-02** | Structure Evaluator | Token overlap cannot recognize semantically similar structure names. | Replace `_token_overlap_ratio()` with SentenceTransformer semantic similarity. | `evaluation_structure.py` | 2–3 hrs | ⭐⭐⭐⭐⭐ | Fair evaluation of LLM-generated structure names. |
| **3** | 🔴 Critical | **EVAL-03** | Business Evaluator | Token Jaccard fails on paraphrased business rules. | Replace Jaccard with SentenceTransformer similarity (already started). | `evaluation_business.py` | 1–2 hrs | ⭐⭐⭐⭐⭐ | Correctly identifies semantically equivalent business rules. |
| **4** | 🔴 Critical | **EVAL-04** | Threshold Calibration | Similarity thresholds are arbitrary. | Label 30–50 prediction pairs manually and determine optimal thresholds empirically. | New calibration script | 1 day | ⭐⭐⭐⭐☆ | Makes evaluation scientifically defensible. |
| **5** | 🔴 Critical | **EVAL-05** | Existing Benchmark Results | All previous metrics were generated with a flawed evaluator. | Re-evaluate saved JSON outputs using the corrected evaluator. | Evaluation runner | 2–3 hrs | ⭐⭐⭐⭐⭐ | Produces valid benchmark results without rerunning LLMs. |
| **6** | 🟠 High | **EVAL-06** | Evaluator Validation | No evidence that evaluator agrees with human judgment. | Compare evaluator decisions with manual assessment on 20–50 samples. | Validation script | 4–6 hrs | ⭐⭐⭐⭐☆ | Increases trustworthiness of the benchmark. |
| **7** | 🟠 High | **EVAL-07** | Experiment Repository | Predictions and evaluation results are not stored comprehensively. | Save raw output, parsed JSON, evaluation details, metrics, and metadata for every run. | Result logger | 2–3 hrs | ⭐⭐⭐⭐☆ | Improves reproducibility and future analysis. |
| **8** | 🟠 High | **EVAL-08** | Malformed Output Detection | Extremely large outputs (e.g., 105 predictions vs. 11 ground truth) distort averages. | Flag malformed runs instead of averaging them with valid runs. | `evaluation_business.py` / reporting | 1 hr | ⭐⭐⭐☆☆ | Prevents misleading benchmark statistics. |
| **9** | 🟡 Medium | **EVAL-09** | Error Reporting | Only reports Correct, Partial, Missing, Hallucinated. | Add reasons for partial matches and summary statistics. | Reporting module | 2–3 hrs | ⭐⭐⭐☆☆ | Strengthens discussion and error analysis. |
| **10** | 🟡 Medium | **EVAL-10** | Benchmark Reporting | Result tables are basic. | Generate benchmark-style comparison tables and per-model summaries. | Report generation | 3–4 hrs | ⭐⭐⭐☆☆ | Makes results easier to understand and publish. |

---

# **What Should NOT Be Changed**

| Component | Recommendation | Reason |
| ----- | ----- | ----- |
| COBOL Dataset | ✅ Keep | Already complete and manually annotated. |
| Prompt Strategies | ✅ Keep | Sufficient for answering your research questions. |
| LLM Pipeline | ✅ Keep | Stable and functioning correctly. |
| JSON Schema | ✅ Keep | Only minor alias fixes are required. |
| Annotation Format | ✅ Keep | Already serves as your gold standard. |
| Overall Thesis Pipeline | ✅ Keep | No redesign is needed. |
| CBS Formula | ✅ Keep (unless calibration suggests otherwise) | Maintain consistency across experiments. |
| Entire Evaluation Framework | ❌ Do not rewrite | Fix the existing evaluator instead of replacing it. |

---

# **Expected Outcome After Completing These Steps**

| Area | Current Status | Expected Status |
| ----- | ----- | ----- |
| Structure Evaluation | ❌ Incorrect (`Correct = 0`) | ✅ Reliable semantic matching |
| Business Evaluation | ⚠️ Underestimates LLM performance | ✅ Fair semantic evaluation |
| Benchmark Results | ❌ Not trustworthy | ✅ Scientifically defensible |
| Model Comparison | ⚠️ Potentially misleading | ✅ Accurate comparison across models |
| Methodology | Good | Excellent (with validated evaluator) |
| Reproducibility | Moderate | High |
| Thesis Quality | Good implementation, weak evaluation | Strong implementation with strong evaluation |

### **Recommended Execution Order**

| Order | Task | Complete Before Next? |
| ----- | ----- | ----- |
| 1 | Fix structure evaluator (`structure_name` \+ semantic matching) | ✅ Yes |
| 2 | Fix business evaluator (semantic similarity) | ✅ Yes |
| 3 | Calibrate thresholds | ✅ Yes |
| 4 | Re-evaluate all saved outputs | ✅ Yes |
| 5 | Validate evaluator against manual judgments | ✅ Yes |
| 6 | Save complete experiment repository | ✅ Yes |
| 7 | Regenerate tables, graphs, and benchmark reports | ✅ Yes |
| 8 | Update methodology, results, discussion, and conclusion | Final step |

This plan keeps your **implementation stable**, fixes the **core scientific weakness** (the evaluation), and minimizes unnecessary changes while maximizing the credibility of your thesis.

how i can do this?

Good question. Instead of giving you generic advice, I'll tell you **exactly what I would do if I were implementing your thesis**.

Your evaluation is **about 80% correct already**. We don't need to redesign it—we need to **fix and validate it**.

---

# **Phase 1 – Fix the Evaluator (Highest Priority)**

| Step | What to Do | Files | Time | Difficulty |
| ----- | ----- | ----- | ----- | ----- |
| 1.1 | Verify the actual JSON fields produced by every LLM | Saved JSON outputs | 30 min | Easy |
| 1.2 | Fix `_normalize_structure()` to support all field aliases | `evaluation_structure.py` | 15 min | Easy |
| 1.3 | Replace token overlap with semantic similarity for structure names | `evaluation_structure.py` | 1–2 hrs | Medium |
| 1.4 | Keep SentenceTransformer for business evaluator | `evaluation_business.py` | Done | — |
| 1.5 | Remove the hard line-overlap filter only if your annotations show legitimate matches without overlap | `evaluation_business.py` | 30 min | Medium |

---

## **Step 1.1 (Most Important)**

Before changing any code, answer this question:

**What do the LLMs actually produce?**

For example,

GPT may output

{  
   "structure\_name":"PROCESS CUSTOMER"  
}

Claude may output

{  
   "name":"PROCESS CUSTOMER"  
}

Gemini may output

{  
   "structureName":"PROCESS CUSTOMER"  
}

Until you know this, you shouldn't modify `_normalize_structure()`.

---

# **Phase 2 – Calibrate Thresholds**

This is the step most theses skip.

---

### **Create a validation dataset**

Take

* 50 structure matches  
* 50 business rule matches

Make a spreadsheet.

Example

| Ground Truth | Prediction | Human Decision |
| ----- | ----- | ----- |
| Initialize Customer | Customer Initialization | Correct |
| Read File | Open Customer File | Correct |
| Reject Claim | Accept Claim | Incorrect |

---

Run

semantic\_similarity()

on every pair.

Result

| Human | Similarity |
| ----- | ----- |
| Correct | 0.94 |
| Correct | 0.89 |
| Partial | 0.71 |
| Partial | 0.63 |

Now choose

Threshold \= 0.78

because it separates the groups best.

Now your thesis can say

The threshold was empirically determined using manually labeled examples.

---

# **Phase 3 – Re-evaluate Everything**

This is where you save time.

Current

LLM

↓

Evaluation

Don't rerun the LLMs.

Instead

Saved JSON

↓

New Evaluator

↓

New Metrics

This should take minutes rather than days.

---

# **Phase 4 – Validate the Evaluator**

Take

20 random outputs.

Read them yourself.

Example

| Human | Evaluator |
| ----- | ----- |
| Correct | Correct |
| Correct | Correct |
| Partial | Partial |

If

18/20

agree

that's

90%

agreement.

Mention this in the thesis.

---

# **Phase 5 – Save Every Experiment**

Right now

you probably save

metrics.csv

Instead

save

experiment.jsonl

Each line

{  
 "model":"GPT-5",  
 "prompt":"Few-shot",  
 "file":"VSCBEX01",  
 "prediction":{...},  
 "evaluation":{...},  
 "metrics":{...}  
}

Now

nothing is lost.

---

# **Phase 6 – Better Reporting**

Instead of

Correct

Partial

Missing

also report

| Metric |
| ----- |
| Average Semantic Similarity |
| Structural Fidelity |
| Hallucination Rate |
| Completeness |
| Precision |
| Recall |
| CBS |

Most of these are already available.

---

# **What I Need From You to Help Implement This**

Here is the order I would follow.

| Step | What I Need | Why |
| ----- | ----- | ----- |
| 1 | One actual **LLM output JSON** (GPT) | Verify field names |
| 2 | One **Claude output JSON** | Check schema consistency |
| 3 | One **Gemini output JSON** | Check schema consistency |
| 4 | One **ground-truth annotation JSON** | Compare with predictions |
| 5 | Your current **evaluation runner** (the script that calls `evaluate_structure()` and `evaluate_business()`) | See how metrics are computed and stored |
| 6 | One **experiment result file** (`log.jsonl` or similar) | Verify what is already saved |

---

# **My Recommendation**

Don't try to fix everything in one go.

I recommend this sequence:

1. **Inspect the actual LLM JSON outputs.**  
2. **Fix the evaluator based on those outputs.**  
3. **Run the evaluator on existing saved results.**  
4. **Check 20 samples manually.**  
5. **Only after you're satisfied, regenerate the final tables and graphs.**

This minimizes risk and avoids wasting time rerunning expensive experiments.

## **I think we can finish the evaluation in 2–3 working days, but I don't want to guess anymore.**

The next thing I want to do is inspect **real outputs**, not code. If you send me:

* one GPT output,  
* one Claude output,  
* one Gemini output,  
* one ground-truth annotation,

I'll tell you **exactly** what needs to change in the evaluator—and what doesn't. That will eliminate the remaining uncertainty.

give the result of phase in tabular form

Below is the **recommended implementation roadmap** that I would give you as your supervisor. The phases are ordered by **dependency**, meaning **Phase 2 should only start after Phase 1 is complete**, and so on.

| Phase | Priority | Objective | Tasks | Deliverables | Success Criteria | Estimated Effort | Thesis Impact |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **Phase 1** | 🔴 Critical | **Fix Evaluation Logic** | • Verify actual LLM JSON schema • Fix `structure_name` mapping • Replace token similarity with semantic similarity for structure names • Replace Jaccard with SentenceTransformer for business rules | Corrected `evaluation_structure.py` and `evaluation_business.py` | Evaluation no longer produces `Correct = 0` for all runs | **1–2 days** | ⭐⭐⭐⭐⭐ Very High |
| **Phase 2** | 🔴 Critical | **Calibrate Evaluation Thresholds** | • Select 30–50 representative prediction pairs • Manually label Correct/Partial/Incorrect • Compute semantic similarity scores • Select optimal thresholds | Calibrated similarity thresholds with documented justification | Thresholds are experimentally justified instead of arbitrary | **1 day** | ⭐⭐⭐⭐☆ High |
| **Phase 3** | 🔴 Critical | **Re-evaluate Existing Results** | • Run corrected evaluator on all saved JSON outputs • Do not rerun LLMs • Generate updated metrics | New evaluation results for every previous experiment | Updated benchmark metrics generated successfully | **0.5 day** | ⭐⭐⭐⭐⭐ Very High |
| **Phase 4** | 🟠 High | **Validate the Evaluator** | • Randomly select 20–50 evaluated samples • Compare evaluator labels with manual judgments • Calculate agreement rate | Validation report showing evaluator reliability | ≥85–90% agreement between evaluator and manual review | **0.5–1 day** | ⭐⭐⭐⭐☆ High |
| **Phase 5** | 🟠 High | **Improve Experiment Management** | • Save every experiment (prompt, model, raw output, parsed JSON, evaluation, metrics) • Store in JSONL/CSV | Complete experiment repository | Every experiment is reproducible | **0.5 day** | ⭐⭐⭐⭐☆ High |
| **Phase 6** | 🟡 Medium | **Improve Reporting & Analysis** | • Flag malformed runs • Generate benchmark tables • Create comparison graphs • Add error summaries | Final benchmark report with tables and figures | Clear comparison across models and prompt strategies | **1 day** | ⭐⭐⭐☆☆ Medium |
| **Phase 7** | 🟢 Low | **Update Thesis Writing** | • Update Methodology chapter • Update Results chapter • Expand Discussion • Revise Conclusion | Final thesis draft | Thesis accurately reflects corrected evaluation and findings | **2–3 days** | ⭐⭐⭐⭐⭐ Very High |

---

# **Expected Outcome After Each Phase**

| Phase | Before | After |
| ----- | ----- | ----- |
| **Phase 1** | Evaluator incorrectly scores most outputs (`Correct = 0`) | Fair semantic evaluation with valid matching |
| **Phase 2** | Arbitrary thresholds | Scientifically justified thresholds |
| **Phase 3** | Old, unreliable benchmark results | Updated and trustworthy benchmark results |
| **Phase 4** | No proof evaluator is correct | Evaluator validated against human judgment |
| **Phase 5** | Partial experiment records | Fully reproducible experiment repository |
| **Phase 6** | Basic result presentation | Publication-quality benchmark tables and graphs |
| **Phase 7** | Draft thesis | Final, defensible thesis ready for submission |

---

