# Prompt Pairwise Experiment 001

## What changed

Prompt v1 used the existing W4 baseline with no system prompt.

Prompt v2 added one explicit instruction:

> Answer only questions that can be answered from FastAPI documentation. If a
> question is outside FastAPI documentation, do not answer from general
> knowledge and do not make recommendations. Instead say that the available
> FastAPI documentation is insufficient to answer the question.

The purpose of this change was to improve handling of out-of-scope questions,
especially the weak behavior observed for golden-set case g020.

## Aggregate result

The 20-question golden set was evaluated using a pairwise judge with position
flipping.

Results:

- v1 wins: 5
- v2 wins: 4
- ties: 2
- ambiguous: 9
- position-bias rate: 30.0%
- wall-clock time: 153.43 seconds

The high number of ambiguous results and the 30% position-bias rate indicate
that the pairwise judge was not sufficiently stable on answers that were very
similar in quality.

## Findings

Prompt v2 clearly improved the intended failure mode. For g020, the original
prompt answered the database-selection question using general knowledge,
whereas v2 correctly responded that the available FastAPI documentation was
insufficient.

The pairwise judge consistently preferred v2 for g020 after position flipping.

However, many normal FastAPI questions produced answers that were very close in
quality. On cases such as g005 and g006, the judge sometimes selected a winner
in one ordering and returned a tie or different preference after the answers
were reversed. This suggests sensitivity to answer position and small wording
differences.

The experiment therefore provides stronger evidence for the out-of-scope
behavior improvement than for an overall quality improvement across the full
golden set.

## Decision

Keep the explicit out-of-scope instruction from prompt v2 because it directly
addresses the known boundary failure without changing the intended FastAPI
scope.

Do not interpret the aggregate pairwise win counts as strong evidence that v2
is globally better, because the 30% position-bias rate exceeds the acceptable
threshold and 9 of 20 comparisons were ambiguous.

Future pairwise evaluation should use a more stable judging rubric or an
additional adjudication step for ambiguous comparisons.