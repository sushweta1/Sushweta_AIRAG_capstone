# AI-RAG Capstone — Consolidated Development History

## Project Overview

Project: FastAPI Knowledge Assistant
Repository: Sushweta_AIRAG_capstone
Development period: Weeks 1–9

This document consolidates the development milestones,
implementation artifacts, and GitHub check-in history
for the AI-RAG capstone through Week 9.

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

## Week 8 — Advanced Ingestion, Metadata and Privacy

Focus:
Extend the RAG pipeline to support multi-format documents,
structure-aware chunking, metadata enrichment, and PII redaction.

Implementation:
- Seven HR/IT policy documents
- PDF, DOCX, HTML and Markdown parsing
- Structure-aware chunking
- Metadata enrichment and payload indexing
- Regex-based PII redaction
- Known-person-name redaction
- Phone-number redaction regression tests
- Qdrant collection: capstone_chunks_v2
- Redacted collection: capstone_chunks_v2_redacted
- 24 structure-aware chunks
- text-embedding-3-small embeddings

Evidence:
- week08/src/ingest/
- week08/src/rag/qdrant_store.py
- week08/scripts/ingest_corpus.py
- week08/scripts/audit_pii.py
- week08/scripts/compare_v1_vs_v2.py
- week08/tests/test_w8.py
- week08/tests/test_name_redaction_pipeline.py
- week08/tests/test_phone_pii_regression.py
- week08/docs/experiments/wk8-matched-baseline.md
- week08/docs/adr/0001-capstone-framing.md

Matched evaluation:
Both collections used the same seven HR/IT documents,
embedding model and 20-question golden dataset.

| Metric | W7 matched baseline | W8 redacted |
|---|---:|---:|
| Chunks | 16 | 24 |
| Source hit rate | 100% | 100% |
| Total cost | $0.00185 | $0.00152 |
| Latency p50 | 1143 ms | 1172 ms |
| Latency p95 | 1809 ms | 1530 ms |

Privacy improvements:
- Expanded redaction after manual review.
- Seven specifically checked identifiers were absent
  from the regenerated local review file.
- Original documents were excluded from GitHub.
- Previously ingested collections were preserved.

Evaluation limitations:
- The original comparison against the FastAPI corpus
  was invalid because the source documents differed.
- A matched HR/IT baseline was created instead.
- Source-hit accuracy does not establish answer correctness.
- Redaction is rule-based and is not comprehensive NER.
- Performance measurements represent individual runs.

Outcome:
Implemented advanced ingestion and privacy controls
while maintaining source-hit performance on the
matched evaluation dataset.

Repository integration:
- Week 8 implementation preserved under week08/.
- Implementation commit: 51f7902
- Pull request #1 merged: 15976a2


## Week 9 — Hybrid Retrieval, Reranking and Query Rewriting

Focus:
Evaluate advanced retrieval strategies and determine
whether additional retrieval complexity improves relevance.

Implementation:
- Dense vector retrieval
- BM25 sparse keyword retrieval
- Hybrid retrieval using Reciprocal Rank Fusion
- RRF constant: k=60
- Cross-encoder reranking
- Lazy-loaded ms-marco-MiniLM-L-6-v2 model
- HyDE query rewriting
- Multi-query rewriting
- Step-back query rewriting
- Retrieval method selection through ask_rag()
- Precision@3 and Precision@5 evaluation
- Existing Week 8 Qdrant collection reused
- Collection: capstone_chunks_v2
- 24 existing chunks; no reingestion required

Evidence:
- week09/src/rag/retrieval.py
- week09/src/rag/query_rewrite.py
- week09/src/rag/qdrant_rag.py
- week09/scripts/compare_retrieval_methods.py
- week09/scripts/compute_precision_at_k.py
- week09/scripts/try_query_rewrite.py
- week09/tests/test_w9.py
- week09/verify_w9.py
- week09/docs/wk9-retrieval-comparison.md
- week09/docs/wk9-precision-delta.md
- week09/docs/wk9-query-rewrite-trial.md
- week09/docs/kpi/wk9-snapshot.md
- week09/docs/adr/0001-capstone-framing.md

Retrieval comparison:

| Metric | Dense | Hybrid | Hybrid + rerank |
|---|---:|---:|---:|
| Source hits | 20/20 | 20/20 | 20/20 |
| Source hit rate | 100% | 100% | 100% |
| Total cost | $0.00152 | $0.00152 | $0.00154 |
| E2E p50 | 1842 ms | 1619 ms | 2154 ms |
| E2E p95 | 2702 ms | 2229 ms | 8362 ms |

Precision experiment:

| Metric | Dense | Hybrid | Hybrid + rerank |
|---|---:|---:|---:|
| Precision@3 | 0.733 | 0.700 | 0.667 |
| Precision@5 | 0.540 | 0.540 | 0.480 |
| Retrieval p50 | 34 ms | 34 ms | 441 ms |
| Retrieval p95 | 39 ms | 36 ms | 728 ms |

Query rewriting experiment:
- Technique: HyDE
- Baseline Precision@3: 0.667
- HyDE Precision@3: 0.550
- Delta: -0.117
- Improved questions: 1
- Deteriorated questions: 7
- Unchanged questions: 12
- Decision: DROP HyDE as a default retrieval strategy.
- Multi-query and step-back were functionally verified
  but not benchmarked for comparative effectiveness.

Golden dataset correction:
- Initial measured source hit rate: 45%.
- Eleven expected_source values used obsolete filenames.
- expense_policy.md changed to expense_policy.pdf.
- vpn_setup.md changed to vpn_setup.html.
- security_incident.md changed to security_incident.docx.
- Corrected measured source hit rate: 100%.
- No retrieval algorithm or Qdrant data was changed
  during this correction.
- The increase reflects evaluation-label correction,
  not an improvement in retrieval quality.
- Corresponding files were assumed to represent the
  same policies; content equivalence was not independently
  established.

Technical issues resolved:
- Reactivated the Qdrant Cloud cluster.
- Restored authenticated Qdrant connectivity.
- Added the missing python-dotenv dependency.
- Implemented automatic environment loading.
- Preserved externally supplied environment variables.
- Updated the shell launcher to initialize credentials.
- Isolated verifier-generated experiment reports.
- Verified all three full experiment reports remained
  unchanged using SHA-256 checksums.
- Excluded credentials, raw corpus, generated embeddings
  and temporary verification reports from Git.

Verification:

| Metric | Original package | Integrated repository |
|---|---:|---:|
| Verification checks | 40/40 | 40/40 |
| Smoke tests | 16/16 | 16/16 |
| Dense latency | 3166 ms | 3109 ms |
| Hybrid + rerank latency | 4380 ms | 3508 ms |
| Verification spend | $0.0011 | $0.0010 |

Additional validation:
- Seven Qdrant collections accessible.
- Existing collection contains 24 points.
- Eight payload indexes verified.
- All three retrieval modes operational.
- All three query rewrite techniques operational.
- Full experiment report integrity: 3/3 PASS.
- Automated credential scan: 37 files, zero findings.
- Automated sensitive-data scan: 9 files, zero findings.

Architectural decisions:
- Retain dense retrieval as the default.
- Keep hybrid retrieval available as an alternative.
- Keep cross-encoder reranking experimental.
- Do not enable HyDE by default.
- Preserve Week 9 as an isolated implementation under
  week09/ to avoid breaking earlier API contracts.
- Preserve the existing Week 1-8 implementation.

Limitations:
- Source-level precision is a proxy for relevance.
- Answer correctness, faithfulness and hallucination
  rates were not measured by these experiments.
- The benchmark contains only 20 questions and 24 chunks.
- Dense latency passed the verifier threshold of 5 seconds
  but missed the aspirational sub-second target.
- Hybrid + rerank passed the 6-second threshold
  but missed the aspirational 2-second target.
- Fresh installation using --install was not tested.
- Automated privacy scans are not comprehensive.
- Public sharing requires confirmation of data permissions.
- Week 9 is a separate curriculum snapshot, not a fully
  unified application containing every Week 8 custom fix.
- Raw corpus and credentials are not included in GitHub;
  external configuration is required for reproduction.

Outcome:
Implemented and evaluated advanced retrieval strategies,
completed all 40 verification checks, and established
an evidence-based recommendation to retain dense
retrieval as the default on the current benchmark.

Repository integration:
- Week 9 isolated under week09/.
- Integration branch: integrate-week9.
- Integrated verification completed successfully.
- Commit, push and pull request merge pending
  at the time of this documentation update.


## GitHub Commit History

The following commits were recorded before the
Week 9 integration commit:

| Commit | Description |
|---|---|
| 5ae8ee2 | Complete Week 6 RAG pipeline and evaluation |
| 809c81b | Week 7: Integrate Qdrant Cloud RAG and evaluation |
| 6d6490a | Docs: Consolidate Week 1-7 capstone development history |
| 51f7902 | Add Week 8 RAG ingestion, PII redaction and evaluation |
| 15976a2 | Merge pull request #1 for Week 8 integration |

Week 9 development and validation are documented
on the integrate-week9 branch.

Git history remains the authoritative record of
subsequent commits and merges.


## Check-in Clarification

The repository contains development artifacts
representing Weeks 1-9.

Weeks 1-5 were not recorded as separate historical
commits. Their accumulated work was included in
the initial Week 6 commit.

Week 7 was subsequently committed independently.

Week 8 was integrated through a separate branch
and merged pull request.

Week 9 follows the isolated weekly implementation
approach to preserve earlier interfaces and artifacts.

This document records the development progression
without modifying or recreating historical commits.


## Final Project Status — Through Week 9

| Milestone | Status |
|---|---|
| Week 1-5 application foundations | Complete |
| Week 6 JSON-based RAG | Implemented and evaluated |
| Week 7 Qdrant migration | Implemented and evaluated |
| Week 8 ingestion and PII redaction | Implemented and merged |
| Week 9 advanced retrieval | Implemented and evaluated |
| Week 9 query rewriting | Implemented and evaluated |
| Week 9 integrated verification | 40/40 PASS |
| Week 9 smoke tests | 16/16 PASS |
| Week 9 experiment report integrity | 3/3 PASS |
| Week 9 KPI snapshot | Complete |
| Week 9 ADR | Complete |
| Week 9 automated security scans | Zero findings |
| Week 9 GitHub publication | Pending |

Key architectural outcome:
Dense retrieval remains the recommended default
for the current benchmark. Hybrid retrieval,
reranking and query rewriting remain available
for controlled experimentation.

The consolidated development history through Week 9
provides evidence of implementation, evaluation,
architectural decisions, troubleshooting and
incremental repository integration.
