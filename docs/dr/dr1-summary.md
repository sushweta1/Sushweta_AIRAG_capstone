# DR #1 Summary — FastAPI Knowledge Assistant

## 1. What You Built

The capstone is a FastAPI Knowledge Assistant designed to help developers get
concise answers to questions about FastAPI documentation without repeatedly
searching across multiple documentation pages.

Across W1–W5, the initial pipeline evolved into a working API service with
structured Pydantic request and response models, retry handling, streaming,
SQLite persistence, automated tests, model cost measurement, and evaluation
capabilities.

The M1 evaluation framework includes a 20-question golden set containing 14
happy-path questions, 4 harder questions, and 2 edge cases. An LLM-as-judge
scores candidate answers on Accuracy, Groundedness, and Format using a 1–4
rubric. W5 also introduced prompt pairwise comparison with position flipping
and a Critic-Creator loop for iterative answer improvement.

## 2. What You Measured

In W4, I compared `gpt-4o-mini` and `gpt-4o` on the same 10 questions.
`gpt-4o-mini` cost $0.000791 and completed the run in 14.64 seconds, while
`gpt-4o` cost $0.015158 and took 29.25 seconds. The larger model was
approximately 19.2 times more expensive without showing a consistent quality
advantage, so `gpt-4o-mini` remains the default candidate model.

The W5 `eval-run-001` baseline across 20 golden questions produced average
scores of 3.60/4 for Accuracy, 3.80/4 for Groundedness, and 3.75/4 for Format.

The weakest case was g020, an out-of-scope database-selection question. The
baseline answered using general knowledge instead of recognizing that the
available FastAPI documentation was insufficient.

## 3. Top 3 Things to Discuss

First, unsupported-answer handling is the clearest quality gap. Prompt v2 added
an explicit FastAPI-documentation boundary and corrected the g020 failure.

Second, pairwise evaluation was not fully stable. The experiment produced
5 v1 wins, 4 v2 wins, 2 ties, and 9 ambiguous results, with a 30% position-bias
rate. This means aggregate prompt win counts should not yet be treated as strong
evidence when answers are very similar.

Third, the Critic-Creator experiment demonstrated that iterative evaluation can
correct a known failure. On g020, the answer improved from a mean score of 3.33
in Round 1 to 4.00 in Round 2 and met the 3.5 convergence threshold.

## 4. What You'll Defend If Asked

I will defend the decision to keep `gpt-4o-mini` as the default model because
the measured W4 evidence does not justify the substantially higher cost of
`gpt-4o`.

I will also defend keeping the explicit out-of-scope prompt instruction because
it addresses a demonstrated failure mode, while acknowledging that the
pairwise results do not prove that prompt v2 is globally better.

Finally, I will treat the current evaluation as an M1 baseline rather than a
final production-quality benchmark. Future work should strengthen retrieval
and grounding, expand evaluation coverage, improve judge stability, and measure
time-to-information against manual FastAPI documentation search.