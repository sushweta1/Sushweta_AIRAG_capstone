# Evaluation Run 001

## Run Configuration

- Golden set: `data/golden_set.jsonl`
- Total questions: 20
- Candidate model: `gpt-4o-mini`
- Judge: LLM-as-judge
- Scoring dimensions: Accuracy, Groundedness, Format
- Score range: 1–4
- Run label: `eval-run-001`

## Aggregate Results

| Metric | Average Score |
|---|---:|
| Accuracy | 3.60 / 4 |
| Groundedness | 3.80 / 4 |
| Format | 3.75 / 4 |

Overall, the baseline performed strongly on most FastAPI questions, with the
main weakness appearing in handling questions outside the intended FastAPI
documentation scope.

## Lowest-Scoring Cases

### g020 — Database selection

**Scores:** Accuracy 2/4, Groundedness 2/4, Format 3/4

The candidate answered the database-selection question using general knowledge
instead of recognising that the available FastAPI documentation was
insufficient to make the recommendation.

This exposed an important decision-boundary weakness: the assistant should
acknowledge when a question is outside the available documentation rather than
provide an unsupported recommendation.

### g003 — Query parameters

**Scores:** Accuracy 3/4, Groundedness 3/4, Format 3/4

The answer was mostly correct but introduced an unnecessary Pydantic extension
rather than staying focused on the expected FastAPI query-parameter behaviour.

### g005 — Response models

**Scores:** Accuracy 3/4, Groundedness 3/4, Format 4/4

The answer was generally correct but omitted some expected details around
response schema/OpenAPI behaviour and the priority of `response_model`.

### g006 — async def

**Scores:** Accuracy 3/4, Groundedness 4/4, Format 3/4

The answer correctly discussed asynchronous operations but did not clearly
state that a normal `def` can be used when the code does not need or support
`await`.

### g008 — Optional query parameters

**Scores:** Accuracy 3/4, Groundedness 4/4, Format 3/4

The core answer was correct, but it introduced an unnecessary `limit`
parameter that was not required by the question.

## Findings

The baseline performs well on standard FastAPI questions. Most entries received
scores of 3 or 4 across all three dimensions.

The most significant issue is not basic FastAPI knowledge but boundary
handling. In g020, the model confidently answered a question that the available
FastAPI documentation could not support.

This result provides a concrete target for prompt improvement: explicitly
instruct the assistant to acknowledge insufficient FastAPI documentation rather
than answer out-of-scope questions from general knowledge.

## Next Action

Use the g020 failure mode to test a revised prompt containing an explicit
out-of-scope/refusal instruction and compare it with the W4 baseline using
pairwise evaluation.