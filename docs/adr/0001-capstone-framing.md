# ADR-0001: Capstone Framing — FastAPI Knowledge Assistant

- **Status:** v1 Locked
- **Original Draft:** W1
- **Locked:** W5 / M1
- **Author:** Sushweta Biswas

## 1. Context

Developers learning or using FastAPI often need to find answers across multiple
documentation pages covering request validation, dependencies, asynchronous
programming, testing, and deployment.

This capstone builds a Q&A assistant over a selected corpus of official FastAPI
documentation so that users can ask natural-language questions and receive
concise, grounded answers.

The M1 implementation provides a working FastAPI service with structured
responses, streaming, retry handling, cost measurement, SQLite persistence,
testing, and an evaluation framework based on a 20-question golden set.

## 2. Primary User and Stakeholders

The primary users are developers who are learning or using FastAPI and need
quick, reliable answers while developing Python API applications.

Secondary stakeholders include:

- Development teams and technical mentors.
- Documentation and knowledge owners.
- Security and governance stakeholders.
- Project sponsors and technical leadership.

The intended value is to reduce repeated manual documentation searching while
maintaining answer quality, traceability, and appropriate handling of
unsupported questions.

## 3. Solution Framing Canvas

| Box | Decision |
|---|---|
| **Inputs** | A natural-language question about the selected FastAPI documentation. |
| **Outputs** | A concise structured answer grounded in relevant FastAPI documentation. |
| **Tools** | OpenAI model for answer generation; retrieval over FastAPI documentation is planned for later iterations. |
| **Memory** | No durable conversational memory in v1; each question is handled independently. |
| **Autonomy level** | Q&A assistant. It answers questions but does not take external actions. |
| **Decision boundaries** | Answer questions supported by the FastAPI documentation. If the available evidence is insufficient, the assistant should state that rather than answer from unsupported general knowledge. |

## 4. Decisions Locked at M1

| Decision | M1 Choice | Evidence |
|---|---|---|
| **Primary model** | `gpt-4o-mini` | W4 comparison showed no consistent quality advantage for `gpt-4o`; `gpt-4o-mini` cost $0.000791 for 10 questions versus $0.015158 for `gpt-4o`, making `gpt-4o` approximately 19.2× more expensive. |
| **Model performance** | Keep `gpt-4o-mini` as the default candidate model | W4 run completed in 14.64s for `gpt-4o-mini` versus 29.25s for `gpt-4o`. |
| **API contract** | Maintain the existing v1 structured `Answer` contract | W3/W4 API and pipeline tests remain backward compatible; all 23 tests passed after W5 changes. |
| **Evaluation approach** | Golden-set evaluation using an LLM-as-judge | W5 established a 20-entry golden set and scores Accuracy, Groundedness, and Format on a 1–4 scale. |
| **Prompt boundary** | Explicitly refuse unsupported, out-of-scope questions | W5 g020 showed the baseline answering a database-selection question from general knowledge. Prompt v2 correctly identified that FastAPI documentation was insufficient. |

## 5. Sponsor KPIs

| KPI | M1 Measurement | Target by W12 / DR #2 |
|---|---|---|
| **Answer Quality** | Accuracy 3.60/4; Groundedness 3.80/4; Format 3.75/4 across 20 golden questions | ≥ 3.8/4 average on each evaluation dimension |
| **Time to Find Information** | Not yet measured at M1 | Establish a measured baseline and demonstrate reduced time compared with manual documentation search |
| **Unsupported-Answer Handling** | Baseline failure observed on g020; revised prompt correctly refused the tested out-of-scope question | ≥ 90% correct handling on a larger set of unsupported/edge questions |

## 6. Evaluation Baseline

Evaluation run `eval-run-001` used 20 golden-set questions.

| Metric | Result |
|---|---:|
| Golden-set size | 20 |
| Average Accuracy | 3.60 / 4 |
| Average Groundedness | 3.80 / 4 |
| Average Format | 3.75 / 4 |

Most standard FastAPI questions scored strongly.

The weakest case was g020, where the model answered a database-selection
question from general knowledge even though the available FastAPI
documentation was insufficient.

The prompt pairwise experiment tested an explicit documentation-boundary
instruction. Results were 5 v1 wins, 4 v2 wins, 2 ties, and 9 ambiguous
comparisons, with a 30% position-bias rate. Therefore, the aggregate pairwise
win count is not considered strong evidence of overall prompt superiority.

However, v2 clearly corrected the specific g020 unsupported-answer failure.

A Critic-Creator experiment on g020 improved the answer from Accuracy 3,
Groundedness 3, Format 4 (mean 3.33) in Round 1 to 4/4/4 (mean 4.00) in
Round 2, reaching the 3.5 convergence threshold.

## 7. Architecture and API Contract

The application exposes the FastAPI service through:

- `/health` for service health.
- `/ask_batched` for structured non-streaming responses.
- `/ask` for streaming responses.

The structured `Answer` contract contains:

- `content`
- `cost_usd`
- `retries`
- `confidence`
- `sources`
- `schema_version`

SQLite provides persistence for application results and W5 evaluation runs.

The v1 API contract remains backward compatible. Breaking public response
changes require a new API version rather than silently modifying v1.

## 8. Consequences and Risks

### Positive consequences

- Developers can obtain concise FastAPI guidance without manually navigating
  multiple documentation pages.
- The structured API provides a stable interface for clients.
- Real cost measurement makes model economics visible.
- The golden set provides a repeatable quality baseline.
- Evaluation results expose failure modes that are not visible from successful
  demonstrations alone.

### Risks and limitations

- FastAPI documentation changes over time.
- Retrieval is not yet implemented, so grounding remains incomplete at M1.
- Model-generated answers may still contain unsupported information.
- The 20-entry golden set is intentionally small and may not represent every
  production question.
- Pairwise evaluation showed a 30% position-bias rate, indicating that the
  current pairwise judge is not sufficiently stable for close comparisons.
- Time-to-information improvement has not yet been measured.

## 9. Open Questions

1. What retrieval and chunking strategy will provide the strongest grounding
   over the selected FastAPI documentation?

2. How should source citations and confidence be presented so developers can
   quickly verify an answer without creating unnecessary response complexity?

3. How should the evaluation set and judging approach be expanded to measure
   unsupported-answer handling and reduce pairwise judge instability before
   DR #2?

## 10. DR #1 Defence

_To be completed during the DR #1 review._

## 11. Change Log

| Week | Version | Change |
|---|---|---|
| **W1** | v0 Draft | Defined the FastAPI Knowledge Assistant use case, primary input/output, tools, memory, autonomy level, decision boundaries, consequences, and risks. |
| **W4** | v0.x | Added the production-style API contract, structured responses, streaming, cost measurement, model comparison, SQLite persistence, and schema-versioning decisions. |
| **W5** | v1 Locked | Added stakeholder KPIs, 20-question golden-set evaluation baseline, LLM-as-judge evaluation, prompt pairwise findings, Critic-Creator evidence, open questions, and locked the M1 decisions for DR #1. |