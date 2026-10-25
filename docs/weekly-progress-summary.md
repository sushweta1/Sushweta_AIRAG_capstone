# AI-RAG Capstone — Consolidated Development History

## Project Overview

Project: FastAPI Knowledge Assistant
Repository: Sushweta_AIRAG_capstone
Development period: Weeks 1–7

This document consolidates the development milestones,
implementation artifacts, and GitHub check-in history
for the seven-week AI-RAG capstone.

## Week 1 — Project Framing and Initial Exploration

Focus:
Define the capstone scope, stakeholders, and initial
LLM application direction.

Evidence:
- docs/adr/0001-capstone-framing-w1-backup.md
- docs/adr/0001-capstone-framing.md
- docs/adr/0001-stakeholder-map.md
- src/hello_llm.py

Outcome:
Established the project foundation and initial
LLM experimentation.

## Week 2 — API Contract and Application Foundations

Focus:
Define the application API contract and develop
the initial FastAPI application structure.

Evidence:
- docs/adr/0002-api-contract.md
- api/main.py
- src/api/main.py
- docs/runs/01-di.txt
- docs/runs/02-pydantic.txt

Outcome:
Established API design, request/response models,
and foundational application components.

## Week 3 — Application Development and Testing

Focus:
Extend the FastAPI application with asynchronous
processing, testing, and user interface components.

Evidence:
- docs/wk3-stress-notes.md
- docs/runs/03-async.txt
- scripts/stress_test.py
- tests/test_api.py
- tests/test_pipeline.py
- ui/app.py
- ui/app_streamlit.py

Outcome:
Developed and tested the application pipeline,
including API and UI components.

## Week 4 — Reliability, Tokens, and Cost Tracking

Focus:
Improve application reliability, token accounting,
cost estimation, and model comparison.

Evidence:
- src/pipeline/cost.py
- src/pipeline/pipeline.py
- src/pipeline/store.py
- tests/test_cost.py
- tests/test_pipeline_w4.py
- scripts/compare_models.py
- docs/lab4-model-comparison.md

Outcome:
Added token/cost tracking and expanded pipeline
validation and comparison capabilities.

## Week 5 — Evaluation and Prompt Engineering

Focus:
Develop a structured evaluation framework using
golden questions, LLM judging, and prompt comparisons.

Evidence:
- data/golden_set.jsonl
- data/pairwise-001-results.json
- docs/eval-run-001.md
- docs/judge-calibration.md
- docs/prompt-pairwise-001.md
- docs/critic-creator-trace.md
- src/eval/golden.py
- src/eval/judge.py
- src/eval/pairwise.py
- src/eval/critic_creator.py
- scripts/run_pairwise.py
- scripts/run_critic_creator.py

Outcome:
Established a repeatable evaluation framework
for assessing answer quality.

## Week 6 — Retrieval-Augmented Generation

Focus:
Introduce documentation-grounded RAG using a
local JSON embedding index.

Implementation:
- 16 FastAPI documentation files
- 303 indexed chunks
- text-embedding-3-small embeddings
- 1536-dimensional vectors
- Cosine similarity retrieval
- Top-K = 5
- gpt-4o-mini answer generation

Evidence:
- src/rag/naive_rag.py
- scripts/build_index.py
- src/eval/run_eval_rag.py
- docs/adr/0003-rag-architecture.md
- docs/kpi/wk6-snapshot.md
- data/corpus/

Evaluation:
- Accuracy: 3.05
- Groundedness: 3.15
- Format: 3.30
- Overall: 3.17/4

Outcome:
Implemented and evaluated the JSON-based RAG
pipeline while preserving the existing API contract.

## Week 7 — Qdrant Cloud Integration

Focus:
Migrate vector storage and retrieval from the
local JSON index to Qdrant Cloud.

Implementation:
- Qdrant collection: capstone_chunks
- Migrated vectors: 303
- Vector dimensions: 1536
- Distance metric: Cosine
- Default retrieval depth: Top-K = 5
- FastAPI /ask_batched integration
- SQLite persistence preserved

Evidence:
- src/rag/qdrant_store.py
- src/rag/qdrant_rag.py
- scripts/migrate_to_qdrant.py
- src/eval/run_eval_qdrant.py
- docs/adr/0004-qdrant-migration.md
- docs/kpi/wk7-snapshot.md

Evaluation:
- Golden questions: 20
- Accuracy: 3.10
- Groundedness: 3.15
- Format: 3.35
- Overall: 3.20/4

Outcome:
Successfully migrated RAG retrieval to Qdrant
Cloud while maintaining comparable answer quality.

## GitHub Commit History

The repository contains two recorded commits.

### Commit 1

Commit: 5ae8ee2
Message: Complete Week 6 RAG pipeline and evaluation

This initial repository commit consolidated the
existing project artifacts developed through Week 6.

It includes evidence of work from Weeks 1–6.

### Commit 2

Commit: 809c81b
Message: Week 7: Integrate Qdrant Cloud RAG and evaluation

This commit introduced the Week 7 Qdrant migration,
evaluation, documentation, and dependency updates.

## Check-in Clarification

The repository contains development artifacts
representing all seven weeks.

However, Weeks 1–5 were not recorded as separate
historical commits in this repository.

Their accumulated work was included in the initial
Week 6 commit.

This document records the development progression
without modifying or recreating historical commits.

## Final Project Status

- Week 1–5 development artifacts: Present
- Week 6 JSON-based RAG: Implemented and evaluated
- Week 7 Qdrant RAG: Implemented and evaluated
- Golden-set evaluation: 20 questions
- Week 7 overall score: 3.20/4
- GitHub repository: Published
- Latest implementation commit: 809c81b

The seven-week development history is consolidated
here for project review and submission evidence.
