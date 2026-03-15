# Legacy Business Rule Extraction & Migration using LLMs

## 1. Project Overview

This project implements a controlled, experiment-driven pipeline to study how
**prompt engineering strategies affect Large Language Models (LLMs)**
in understanding and extracting **program structure** and **business logic**
from legacy COBOL systems.

The project is intentionally designed as a **research harness**, not a product.
Its primary goal is **comparative evaluation**, not end-to-end automation.

Key principle: **Prompt strategy is the only experimental variable**. All other
factors (model, temperature, schema, code paths) are fixed.

---

## 2. Research Objective

The core research question is:

> How do different prompt engineering strategies influence the accuracy,
> completeness, and reliability of LLMs when extracting:
> (a) program structure, and
> (b) business logic
> from legacy COBOL code?

This repository operationalizes findings from systematic literature reviews
showing that **structured and incremental prompting** outperforms naive prompting,
especially in regulated or legacy-heavy domains.

---

## 3. Pipeline Architecture

The experiment pipeline follows a layered interpretation model:

```
Load COBOL Code (with line numbers)
          ↓
For each prompt strategy:
  ├─ STRUCTURE INFERENCE
  │   ├─ Call LLM with prompt strategy
  │   ├─ Extract JSON from response
  │   ├─ Validate against StructureOutput schema
  │   └─ Evaluate against structural annotations
  │
  └─ BUSINESS LOGIC INFERENCE
      ├─ Call LLM with prompt strategy
      ├─ Extract JSON from response
      ├─ Validate against BusinessLogicOutput schema
      └─ Evaluate against business logic annotations
```

Each task:

- Is inferred **independently** (no cross-task reuse)
- Has its own **output schema** (strict Pydantic validation)
- Is evaluated against **separate ground truth** annotations
- Produces **metrics** logged for comparison

---

## 4. What This Project Is (and Is Not)

### This project IS:

- A controlled experiment runner
- A prompt-strategy comparison framework
- A schema-driven LLM evaluation pipeline
- Human-in-the-loop by design
- Transparent and reproducible

### This project is NOT:

- A compiler or automated migration tool
- A full production system
- An autonomous agent system
- A fine-tuned model or RAG system
- An orchestration framework with retries or complex recovery

---

## 5. Key Features

### 5.1 Ghost Data Leak Prevention

All tracking variables are **reset at the beginning of each model iteration**:

- `parsed` (structured output)
- `validation_status` (pass/fail/error)
- `evaluation_metrics` (correct/missing/hallucinated counts)

This ensures previous model results cannot contaminate subsequent runs,
maintaining experimental validity.

**Why this matters**: Without resets, bugs in error handling could cause one
model's failed output to leak into the next model's evaluation, producing
false equivalence in results.

### 5.2 Robust JSON Extraction

LLMs often wrap JSON in markdown code blocks, explanations, or XML tags.
The extraction pipeline:

1. Searches for markdown code blocks (`\`\`\`json ... \`\`\``)
2. Finds first `{` and last `}` for raw JSON
3. Attempts parsing from substring
4. Logs extraction failures clearly

This handles common LLM response patterns without assuming perfect formatting.

**Why this matters**: Claude, Gemini, and other models frequently wrap JSON
in explanatory text or markdown. Manual substring extraction is more robust
than regex or library-based parsing for this use case.

### 5.3 Schema-Driven Validation

Pydantic schemas enforce strict output structure:

- **StructureOutput**: Program name, list of structures with types, line ranges
- **BusinessLogicOutput**: Program name, list of business rules with evidence

Validation failures are recorded as data, not silently corrected.

**Why this matters**: Silent correction hides model failures and skews metrics.
Treating validation failures as data allows researchers to identify systematic
weaknesses in prompt strategies.

### 5.4 Line-Overlap Evaluation

Evaluation uses **line-based matching**, not text-based:

- **Structures**: Matched by line range overlap and name token similarity
- **Business Rules**: Matched by evidence line overlap and rule statement similarity

This approach:

- Grounds inferred items in source code
- Allows for paraphrasing (token overlap >= 0.5)
- Prevents spurious matches from similar text
- Separates CORRECT, PARTIAL, MISSING, and HALLUCINATED items

---

## 6. Data Layers (Assets)

All data lives under `assets/raw/` and is immutable once added.

### 6.1 Raw Source Code

```
assets/raw/COBOL Program/
├── VSCBEX01.cbl
├── VSCBEX02.cbl
└── ...
```

- Original COBOL source, loaded line-by-line
- Line numbers preserved for grounding

### 6.2 Structural Annotations (Ground Truth)

```
assets/raw/Annotated data/
├── VSCBEX01.json
├── VSCBEX02.json
└── ...
```

Structure of each file:

```json
{
  "program_name": "VSCBEX01",
  "structures": [
    {
      "id": "struct_1",
      "structure_type": "DIVISION",
      "name": "DATA DIVISION",
      "lines": [10, 50],
      "description": "..."
    }
  ]
}
```

Used ONLY for structure task evaluation.

### 6.3 Business Logic Annotations (Ground Truth)

```
assets/raw/Business Logic/
├── VSCBEX01.json
├── VSCBEX02.json
└── ...
```

Structure of each file:

```json
{
  "program_name": "VSCBEX01",
  "rules": [
    {
      "rule_id": "rule_1",
      "rule_statement": "Calculate monthly tax...",
      "source_lines": [45, 60],
      "domain": "TAX_PROCESSING"
    }
  ]
}
```

Used ONLY for business logic task evaluation.

---

## 7. Inference Tasks

### Task 1: Structure Inference

**Goal**: Identify program constructs and their organizational roles

**Input**:

- COBOL code (with line numbers)
- Prompt strategy template

**Output**: StructureOutput containing:

- Program name
- Language
- List of structures with:
  - Type (DIVISION, SECTION, PARAGRAPH, LOOP, FILE_OP, CONDITIONAL)
  - Name
  - Line range
  - Description
  - Parent reference

**Validation**: Pydantic schema validation (strict, no corrections)

**Evaluation**: Line overlap + name token matching against annotated structures

---

### Task 2: Business Logic Inference

**Goal**: Infer domain-level system behavior and business guarantees

**Input**:

- COBOL code (with line numbers)
- Prompt strategy template
- (Optionally: inferred structure from Task 1)

**Output**: BusinessLogicOutput containing:

- Program name
- List of business rules with:
  - Rule statement (natural language intent)
  - Rule category (BUSINESS / TECHNICAL / ERROR_HANDLING)
  - Domain (business domain)
  - Evidence (source structures and lines)
  - Confidence (high / medium / low)
  - Assumptions (list)

**Validation**: Pydantic schema validation (strict, no corrections)

**Evaluation**: Evidence line overlap + rule statement similarity matching

---

## 8. Prompt Engineering Strategies (Experimental Variable)

The ONLY experimental variable is **prompt strategy**. All other factors are fixed.

### Evaluated Strategies (in `prompts/` directory)

Stored in:

- `prompts/structure_prompts.json` - strategies for structure task
- `prompts/business_prompts.json` - strategies for business logic task

Each file contains a `strategies` dict:

```json
{
  "strategies": {
    "naive": "Extract structures from: {code}",
    "structured": "Step 1: ... Step 2: ... {code}",
    "incremental": "First reason about... Then extract... {code}"
  }
}
```

Examples:

1. **Naive**: Single instruction, no decomposition
2. **Structured**: Explicit task steps, clear constraints
3. **Incremental/CoT**: Explicit reasoning phases, reasoning hidden from output

---

## 9. Evaluation Approach

### Structure Evaluation

**Matching Algorithm**:

1. For each annotated structure, find best-matching inferred structure by line overlap
2. If no overlap → MISSING
3. If overlap found:
   - Check name token similarity (>= 0.5 → CORRECT, < 0.5 → PARTIAL)
4. Unmatched inferred structures → HALLUCINATED

**Metrics**: Counts of correct, partial, missing, hallucinated

**Output**: Detailed report with matched pairs, similarities, and source line evidence

---

### Business Logic Evaluation

**Matching Algorithm**:

1. For each annotated rule, find best-matching inferred rule by evidence line overlap
2. If no overlap → MISSING (rule not detected)
3. If overlap found:
   - Check rule statement token similarity (>= 0.5 → CORRECT, < 0.5 → PARTIAL)
4. Unmatched inferred rules → HALLUCINATED (LLM made it up)

**Metrics**: Counts of correct, partial, missing, hallucinated

**Output**: Detailed report with matched pairs, similarities, and source line evidence

---

### Result Storage & Aggregation

After all experiments complete, the pipeline stores results in three formats:

**1. Detailed Results** (`experiments/results/results.json`)

- Full `EvaluationResult` objects for every inference
- Includes model, strategy, task, file, validation status
- LLM output and ground truth annotations
- Per-item classifications (correct/partial/missing/hallucinated)
- Link to source evidence with similarity scores

**Example entry**:

```json
{
  "model": "gpt-4",
  "prompt_strategy": "structured",
  "task": "structure",
  "file": "VSCBEX01.cbl",
  "validation_status": "valid",
  "metrics": {
    "correct": 5,
    "partial": 1,
    "missing": 2,
    "hallucinated": 0,
    "completeness": 0.70,
    "hallucination_rate": 0.0
  },
  "details": [
    {
      "predicted": "PROCEDURE DIVISION",
      "ground_truth": "PROCEDURE DIVISION",
      "classification": "correct",
      "similarity_score": 1.0
    },
    ...
  ]
}
```

**2. CSV Summary** (`experiments/results/results_summary.csv`)

- Tabular format for spreadsheet analysis
- One row per result
- Columns: model, strategy, task, file, validation_status, correct, partial, missing, hallucinated, completeness, hallucination_rate
- Ideal for pivot tables and comparative visualization

**3. Aggregate Statistics** (`experiments/results/summary.json`)

- Global metrics across all runs
- Per-model aggregates (total correct/partial/missing/hallucinated)
- Per-task aggregates
- Overall precision, recall, and hallucination rate

**Example**:

```json
{
  "by_model": {
    "gpt-4": {
      "correct": 45,
      "partial": 8,
      "missing": 12,
      "hallucinated": 3,
      "precision": 0.857
    },
    ...
  },
  "by_task": {
    "structure": {
      "correct": 50,
      "partial": 7,
      ...
    },
    ...
  },
  "global": {
    "total_correct": 95,
    "overall_precision": 0.853,
    "overall_recall": 0.847,
    "overall_hallucination_rate": 0.022
  }
}
```

---

### Logging & Debugging

Console output and detailed log are captured separately:

- **Console** (`stdout`): Progress indicators and summary results
- **Log File** (`experiments/run_log.txt`): Timestamped, indented trace of all operations

Log structure:

```
2025-01-15T14:32:01 [INFO] PIPELINE STARTING
2025-01-15T14:32:02 [INFO]   Processing program: VSCBEX01.cbl
2025-01-15T14:32:03 [INFO]     Task: structure / Strategy: incremental
2025-01-15T14:32:04 [INFO]       Model: gpt-4
2025-01-15T14:32:05 [INFO]         LLM call started
2025-01-15T14:32:08 [INFO]         JSON extraction: success
2025-01-15T14:32:08 [INFO]         Schema validation: success
2025-01-15T14:32:08 [INFO]         Evaluation complete - correct=5, partial=1, missing=2, hallucinated=0
```

---

## 10. Execution Flow

### Main Pipeline (main.py)

```python
for each COBOL program:
  for each prompt strategy:
    # Structure task
    for each LLM model:
      Build structure prompt
      Call LLM
      Extract JSON from response
      Validate against StructureOutput schema
      Evaluate against annotated structures
      Log results

    # Business logic task
    for each LLM model:
      Build business prompt
      Call LLM
      Extract JSON from response
      Validate against BusinessLogicOutput schema
      Evaluate against annotated business logic
      Log results
```

### Key Points

- **Variable reset**: All tracking variables reset per model (ghost data leak fix)
- **JSON extraction**: Robust extraction from markdown/XML/plain JSON
- **Schema validation**: Strict, no corrections or coercion
- **Evaluation**: Line-based matching with token similarity secondary filtering
- **Logging**: Structured prints and experiment log entries

---

## 11. Logging & Experiment Tracking

### Structured Print Output

Pipeline stages are logged with indentation for easy readability:

```
[PIPELINE] Starting COBOL extraction pipeline
[PIPELINE] Loaded 5 COBOL programs
[PROGRAM] Processing: VSCBEX01
  [TASK] structure
    [STRATEGY] structured
      [MODEL] gpt-4
        Loading prompt and calling LLM...
        Raw LLM response received
        JSON extraction from raw response completed
        Schema validation: valid
        Running evaluation...
        Evaluation: correct=5, partial=2, missing=1, hallucinated=0
```

This hierarchical logging helps identify:

- Which programs are being processed
- Which strategies are being tested
- Which models are being evaluated
- Where validation failures occur
- What evaluation results are produced

### Experiment Log

Results are appended to `experiments/log.jsonl` as JSON lines.
Each record includes:

- Timestamp
- Program name
- Task (structure / business)
- Prompt strategy
- Model name
- Validation status (valid / invalid / error)
- Evaluation summary (counts: correct, partial, missing, hallucinated)
- Performance metrics (completeness, hallucination_rate, fidelity)
- Raw output length (debugging aid)

Used for comparative analysis across strategies and models.

---

## 12. JSON Extraction Handling

Models like Claude and Gemini wrap JSON in extra text:

**Common Patterns**:

````
Sure! Here's the structure:
```json
{...}
````

Or with markdown:

```
<div>
{"program_name": "..."}
</div>
```

Or with explanation:

```
Based on my analysis, here are the structures:
{
  "program_name": "VSCBEX01",
  ...
}
```

**Extraction Strategy**:

1. Search for markdown code blocks with language identifier (`\`\`\`json`)
2. Extract substring from first `{` to last `}`
3. Parse extracted substring as JSON
4. Log failures for manual review

**Why this is necessary**:

- LLMs don't always return pure JSON
- Markdown wrappers are common in casual responses
- Simple substring extraction is robust and debuggable
- Regex-based extraction would fail on nested structures
- Library-based parsing adds dependencies and complexity

---

## 13. Design Principles

1. **Experimental Clarity**: Prompt strategy is the only variable
2. **No Silent Failures**: Schema validation errors are recorded, not corrected
3. **Line-Based Grounding**: All inferred items must be grounded in source code
4. **Separation of Concerns**: Structure and business logic are independent
5. **Reproducibility**: Deterministic, no random seeds or non-deterministic operations
6. **Transparency**: All logging visible to identify pipeline behavior
7. **Simplicity**: No agents, vector databases, retries, or complex orchestration

---

## 14. Tooling & Environment

- **Python 3.10+**
- **uv**: Dependency and project management
- **Pydantic**: Schema definition and validation
- **LangChain**: LLM orchestration and structured output
- **Pandas**: Data analysis and log processing (optional, for analysis notebooks)

---

## 15. Repository Structure

```
d:/Projects/COBOL Converter/
├── main.py                          # Main experiment loop
├── README.md                        # This file
├── pyproject.toml                   # Project configuration
├── uv.lock                          # Lock file for reproducibility
│
├── assets/raw/
│   ├── COBOL Program/              # COBOL source files (.cbl)
│   ├── Annotated data/             # Structure annotations (.json)
│   └── Business Logic/             # Business rule annotations (.json)
│
├── pipeline/
│   ├── load_data.py                # Load COBOL and annotations
│   ├── llm_call.py                 # LLM caller with JSON extraction
│   ├── llm_factory.py              # LLM factory (model initialization)
│   └── evaluation.py               # (Future) centralized evaluation
│
├── schema/
│   ├── program_structure.py        # StructureOutput Pydantic schema
│   └── business_logic.py           # BusinessLogicOutput Pydantic schema
│
├── evaluation/
│   ├── evaluation_structure.py     # Structure evaluation logic
│   └── evaluation_business.py      # Business logic evaluation logic
│
├── experiments/
│   ├── experiments_log.py          # Logging to log.jsonl
│   ├── constants.py                # File paths and constants
│   └── log.jsonl                   # Experiment results (JSON lines)
│
└── prompts/
    ├── structure_prompts.json      # Structure task prompt strategies
    └── business_prompts.json       # Business logic task prompt strategies
```

---

## 16. Running the Pipeline

### Prerequisites

```bash
# Install dependencies
uv sync

# Set LLM flag (optional, default OFF for dry-run)
export USE_LLM=1
```

### Execute

```bash
# Run the experiment pipeline
uv run main.py
```

### Output

- Structured logs to stdout with pipeline stages
- Experiment results appended to `experiments/log.jsonl`
- Each run adds new records for analysis

---

## 17. Analysis & Interpretation

### Reading Results

The `experiments/log.jsonl` file contains one JSON record per model-task-strategy combination:

```json
{
  "timestamp": "2026-03-15T10:30:45.123Z",
  "program": "VSCBEX01",
  "task": "structure",
  "prompt_strategy": "structured",
  "model": "gpt-4",
  "validation_status": "valid",
  "evaluation": {
    "correct": 5,
    "partial": 2,
    "missing": 1,
    "hallucinated": 0
  },
  "metrics": {
    "completeness": 0.857,
    "hallucination_rate": 0.0,
    "fidelity": 0.875
  },
  "raw_output_length": 2048
}
```

### Interpretation

- **correct**: Inferred items with high semantic match (>= 0.5 token overlap)
- **partial**: Inferred items with lower semantic match (< 0.5)
- **missing**: Annotated items not found in inferred output
- **hallucinated**: Inferred items without annotation matches

**Success Metrics**:

- High `correct`, low `missing` → Good recall
- Low `hallucinated` → High precision
- Consistent across models/strategies → Stable extraction

---

## 18. Known Limitations & Future Work

### Current Limitations

- Manual annotation required (no auto-generation)
- Token overlap (0.5) is a heuristic (may need tuning)
- Limited to COBOL (language-specific patterns may not generalize)
- No advanced NLP (BERT/semantic embedding not used)

### Future Directions

- Semantic similarity (embeddings) for rule matching
- Active learning to prioritize annotation effort
- Cross-language comparison (Java, Python legacy code)
- Fine-tuned models for specific domains
- Integration with actual migration tools

---

## 19. Intended Audience

- **Researchers**: Studying prompt engineering and LLM reliability
- **ML Engineers**: Building AI-assisted code modernization
- **Legacy System Teams**: Understanding automation possibilities
- **Academic Reviewers**: Evaluating prompt methodology
- **Tool Developers**: Building on controlled benchmarks

---

## 20. Citation & Acknowledgments

This project is a research harness designed to support systematic evaluation
of prompt engineering strategies for legacy system analysis. It prioritizes
**reproducibility**, **transparency**, and **experimental validity** over
production performance.

---

## 21. Status

**Version**: 1.0
**Date**: March 2026
**Status**: Experimental research framework
**Stability**: Stable API, ongoing evaluation

This repository is suitable for research use and comparative studies.
Production use requires additional safety, performance, and scale engineering.
