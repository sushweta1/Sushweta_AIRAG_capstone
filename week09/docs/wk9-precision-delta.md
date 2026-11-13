# W9 Precision@k Delta

Golden set: 20 questions. Methods: dense, hybrid, hybrid_rerank. Baseline for delta: `dense`.

## Aggregate

| Method | P@3 | Δ P@3 | P@5 | Δ P@5 | Retrieve p50 | Retrieve p95 |
|---|---|---|---|---|---|---|
| dense | 0.733 | +0.000 | 0.540 | +0.000 | 34ms | 39ms |
| hybrid | 0.700 | -0.033 | 0.540 | +0.000 | 34ms | 36ms |
| hybrid_rerank | 0.667 | -0.067 | 0.480 | -0.060 | 441ms | 728ms |

## Per-question precision@3

| Q | Question | Expected | P@3 dense | P@3 hybrid | P@3 hybrid_rerank |
|---|---|---|---|---|---|
| q01 | How many days of paid annual leave do I get? | leave_policy.md | 0.67 | 0.67 | 1.00 |
| q02 | Can I carry over unused leave to next year? | leave_policy.md | 0.67 | 0.67 | 0.67 |
| q03 | How much parental leave is available? | leave_policy.md | 0.33 | 0.33 | 0.33 |
| q04 | Do I need a doctor's note for sick leave? | leave_policy.md | 0.67 | 0.67 | 0.67 |
| q05 | How many days per week can I work from home? | wfh_policy.md | 1.00 | 0.67 | 0.33 |
| q06 | Can I expense a co-working space membership? | wfh_policy.md | 0.33 | 0.33 | 0.67 |
| q07 | What's the home office equipment allowance? | wfh_policy.md | 0.67 | 1.00 | 0.67 |
| q08 | What are the core hours when working remotely? | wfh_policy.md | 1.00 | 0.33 | 0.67 |
| q09 | What's the meal allowance during US business trave | expense_policy.pdf | 0.67 | 0.67 | 0.33 |
| q10 | How long do I have to submit travel receipts? | expense_policy.pdf | 0.67 | 0.67 | 0.67 |
| q11 | Can I expense a Notion subscription for myself? | expense_policy.pdf | 0.67 | 0.67 | 0.67 |
| q12 | Is there a cap on training expenses? | expense_policy.pdf | 0.67 | 0.67 | 0.67 |
| q13 | How do I reset my VPN password? | vpn_setup.html | 1.00 | 1.00 | 1.00 |
| q14 | What's the IT helpdesk number? | vpn_setup.html | 0.67 | 1.00 | 0.67 |
| q15 | Is the VPN available on mobile devices? | vpn_setup.html | 1.00 | 1.00 | 1.00 |
| q16 | What do I do if my laptop is stolen at the airport | security_incident.docx | 1.00 | 1.00 | 1.00 |
| q17 | What's the security hotline number for urgent out- | security_incident.docx | 1.00 | 0.67 | 0.67 |
| q18 | Will I be punished for reporting a phishing click  | security_incident.docx | 1.00 | 0.67 | 1.00 |
| q19 | How long does it take to get a replacement laptop? | security_incident.docx | 0.33 | 0.67 | 0.33 |
| q20 | Do I need to use the VPN when working from home? | wfh_policy.md | 0.67 | 0.67 | 0.33 |

## Headline (for wk9 snapshot)

- Precision@3 (hybrid+rerank): **0.667** (-0.067 vs dense)
- Precision@5 (hybrid+rerank): **0.480** (-0.060 vs dense)
- Retrieve latency p50: **441ms**, p95: **728ms**
