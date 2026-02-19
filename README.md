# Legacy Business Rule Extraction & Migration using LLMs

## 1. Project Overview

This project implements a controlled, experiment-driven pipeline to study how
**prompt engineering strategies affect Large Language Models (LLMs)**
in understanding and extracting **program structure** and **business logic**
from legacy COBOL systems.

The project is intentionally designed as a **research harness**, not a product.
Its primary goal is **comparative evaluation**, not end-to-end automation.

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

## 3. High-Level Methodology (MO)

The methodology follows a **layered interpretation model**:

Legacy COBOL Code
↓
STRUCTURE INFERENCE (syntax & control flow)
↓
BUSINESS LOGIC INFERENCE (semantic intent)
↓
Evaluation against human annotations

Each layer:

- Is inferred independently
- Has its own output schema
- Is evaluated against a corresponding human-annotated ground truth

No layer is re-evaluated or reused as ground truth for another.

---

## 4. What This Project Is (and Is Not)

### This project IS:

- A controlled experiment runner
- A prompt-strategy comparison framework
- A schema-driven LLM evaluation pipeline
- Human-in-the-loop by design

### This project is NOT:

- A compiler
- A full migration tool
- An autonomous agent system
- A fine-tuned model or RAG system

---

## 5. Data Layers (Assets)

All data lives under the `assets/raw` directory and is immutable once added.

### 5.1 Raw Source Code

assets/raw/COBOL Program
└── VSCBEX01.cob

- Original COBOL source
- Loaded line-by-line with line numbers preserved

### 5.2 Structural Annotations (Ground Truth)

assets/raw/Annotated data
└── VSCBEX01.json

- Human-annotated program structures
- Divisions, sections, loops, file operations
- Used ONLY to evaluate structure inference

### 5.3 Business Logic Annotations (Ground Truth)

assets/raw/Business Logic
└── VSCBEX01.json

- Human-annotated business rules
- Domain intent expressed in natural language
- Used ONLY to evaluate business logic inference

---

## 6. Inference Tasks

### Task 1: Structure Inference

**Goal:** Identify program constructs and their roles
**Input:** COBOL code with line numbers
**Output:** Structured description of program elements
**Evaluation Against:** Structural annotations

### Task 2: Business Logic Inference

**Goal:** Infer domain-level system behavior and guarantees
**Input:** COBOL code (+ optional inferred structure)
**Output:** Business rules with evidence and confidence
**Evaluation Against:** Business logic annotations

---

## 7. Output Schemas (Strict)

All LLM outputs must conform to strict Pydantic schemas.

### 7.1 Structure Output Schema (Conceptual)

- Program name
- Language
- List of structures:
  - structure_type (DIVISION, LOOP, FILE_OP, etc.)
  - name
  - line_range
  - description
  - parent_id

### 7.2 Business Logic Output Schema (Conceptual)

- Program name
- List of business rules:
  - rule_statement (semantic intent)
  - rule_category (BUSINESS / TECHNICAL / ERROR_HANDLING)
  - domain
  - evidence (source structures + lines)
  - confidence
  - assumptions

LLM outputs that fail schema validation are logged as **failures**, not corrected.

---

## 8. Prompt Engineering Strategies (Experimental Variable)

The ONLY experimental variable in this project is **prompt strategy**.

### Strategies evaluated:

1. **Naive Prompting**
   - Single instruction
   - No decomposition

2. **Structured Prompting**
   - Explicit task steps
   - Clear constraints
   - Single inference pass

3. **Incremental / Chain-of-Thought (Hidden)**
   - Explicit reasoning phases
   - Reasoning NOT included in output
   - Confidence used to express uncertainty

All other factors (model, temperature, schema) are fixed.

---

## 9. Evaluation Approach

### Structure Evaluation

- Match inferred structures to ground truth using:
  - Structure type compatibility
  - Line range overlap
  - Name similarity
- Metrics:
  - Precision
  - Recall
  - False positives / negatives

### Business Logic Evaluation

- Match inferred rules to annotated rules using:
  - Domain match
  - Evidence (line overlap)
  - Semantic equivalence (manual + assisted)
- Outcomes:
  - Correct
  - Missing
  - Hallucinated
  - Partial / ambiguous

Manual review is expected and documented.

---

## 10. Execution Flow

Conceptual execution loop:

for each model:
for each task (structure, business):
for each prompt strategy:
build prompt
call LLM
validate output schema
store raw + parsed output
evaluate against ground truth

Each run is logged with:

- Model
- Task
- Prompt strategy
- Validation result
- Evaluation metrics

---

## 11. Tooling & Environment

- Python
- uv (dependency management)
- Pydantic (schema enforcement)
- LangChain (LLM orchestration)

---

## 12. Design Principles (Non-Negotiable)

- Prompt strategy is the only experimental variable
- No schema coercion or silent fixes
- No mixing structure and business logic evaluation
- Failures are data
- Reproducibility > performance
- Clarity > cleverness

---

## 13. Intended Audience

- Researchers studying LLM reliability in legacy systems
- Engineers working on AI-assisted modernization
- Reviewers evaluating prompt-engineering methodologies
- AI tools generating boilerplate under strict constraints

---

## 14. Status

This repository represents an **experimental research framework**.
It is intentionally minimal, transparent, and extensible.
