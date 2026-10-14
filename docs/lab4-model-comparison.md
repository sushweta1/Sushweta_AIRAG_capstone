# W4 Model Comparison



## Test Setup



The same 10 questions from `data/questions.csv` were run against:



- `gpt-4o-mini`

- `gpt-4o`



This resulted in 20 real OpenAI API calls in total.



## Results



| Model | Questions | Total Cost (USD) | Avg Cost / Question | Time |

|---    |---:       |---:               |---:       |---:           |

| gpt-4o-mini | 10 | 0.000791           | 0.000079          | 14.64s |

| gpt-4o | 10       | 0.015158          | 0.001516          | 29.25s |



`gpt-4o` cost approximately 19.2 times more than `gpt-4o-mini` for the same set of questions.



## Reflection

Across the 10-question comparison, I did not see a consistent quality advantage
for `gpt-4o`. Most simple questions produced very similar answers. On the W3
API-contract question, `gpt-4o-mini` stayed focused on backward compatibility,
while `gpt-4o` misinterpreted "W3" as the World Wide Web. Both models also gave
a generic semantic-versioning answer to the schema-version question rather than
the project-specific compatibility rule.

Given that `gpt-4o-mini` cost $0.000791 in total compared with $0.015158 for
`gpt-4o`, the larger model did not justify its approximately 19.2 times higher
cost on this batch.

I would therefore use `gpt-4o-mini` as the default for routine and high-volume
queries. I would use `gpt-4o` only where a concrete quality evaluation shows a
meaningful advantage on more complex reasoning or domain-specific questions,
rather than assuming the larger model is automatically better.


