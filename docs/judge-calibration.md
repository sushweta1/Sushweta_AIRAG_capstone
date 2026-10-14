# W5 Judge Calibration

## Stratified Sample

- Happy-path: g001, g004, g007, g010, g012, g014
- Harder: g015, g016, g018
- Edge: g020

## My Scores

Score each answer from 1–4 for:

- Accuracy
- Groundedness
- Format

Do this blind, without checking the judge's scores.

| Golden ID | Accuracy | Groundedness | Format | My note |
|---|---:|---:|---:|---|
| g001 | 4 | 4 | 2 | It was easier to understand since a sample is given. |
| g004 | 4 | 4 | 4 | Clearly explains dependency injection, its benefits, and Depends. |
| g007 | 4 | 4 | 4 | Example is helpful. |
| g010 | 4 | 4 | 4 | Easy to understand and provides both interfaces and endpoints. |
| g012 | 4 | 4 | 4 | Provides types and parameter constraints without needing a follow-up question. |
| g014 | 4 | 4 | 4 | Clearly explains reusable dependencies and how Depends is used. |
| g015 | 4 | 4 | 4 | Correctly distinguishes path, query, and body parameters. |
| g016 | 3 | 4 | 3 | Mostly correct async guidance, but misses some nuance about when normal def is appropriate. |
| g018 | 4 | 4 | 4 | Clearly explains using shared dependencies for reusable authentication and validation. |
| g020 | 2 | 2 | 3 | Gives general database advice instead of staying within the FastAPI documentation boundary. |

## Post-Reveal Findings

## Post-Reveal Findings

Calibration was performed on a stratified sample of 10 golden-set entries:
6 happy-path, 3 harder, and 1 edge case.

The comparison covered 30 individual dimension scores across Accuracy,
Groundedness, and Format.

Results:

- Exact agreement: 29/30 (97%)
- Within-1 agreement: 29/30 (97%)
- Accuracy exact agreement: 10/10
- Groundedness exact agreement: 10/10
- Format exact agreement: 9/10
- Disagreements greater than 1: 1

The only significant disagreement was g001 Format. I scored the candidate
2/4 while the judge scored it 4/4. On review, my original note stated that
the included example made the answer easier to understand. This supports
a higher Format score, so the disagreement appears to be learner scoring
drift rather than a weakness in the judge or rubric.

No significant disagreement was found for Accuracy or Groundedness.

## Calibration Decision

**Decision: Trust the judge.**

The judge achieved 97% exact agreement and 97% within-1 agreement. This
meets the activity's strong-calibration thresholds of at least 70% exact
agreement and at least 95% within-1 agreement.

The single significant disagreement does not indicate a systematic rubric
or judge problem. Therefore, no rubric sharpening or judge replacement is
required based on this calibration exercise.

The current judge can be used for subsequent evaluation work, while
periodic calibration should continue as the golden set and application
scope evolve.

## Calibration Decision

_To complete after agreement metrics are computed._