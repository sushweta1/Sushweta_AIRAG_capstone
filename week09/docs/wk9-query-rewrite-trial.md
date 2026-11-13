# W9 Query Rewriting Trial — hyde

Golden set: 20 questions. Baseline: hybrid+rerank on original question. Rewrite: hyde applied.

## Aggregate

| Metric | Value |
|---|---|
| Baseline P@3 | 0.667 |
| hyde P@3 | 0.550 |
| Delta | -0.117 |
| Verdict | **DROP** — hurts precision@3 |

## Per-question

| Q | Question | P@3 base | P@3 rewrite | Δ |
|---|---|---|---|---|
| q01 | How many days of paid annual leave do I get? | 1.00 | 0.33 | -0.67 |
| q02 | Can I carry over unused leave to next year? | 0.67 | 0.33 | -0.33 |
| q03 | How much parental leave is available? | 0.33 | 0.33 | +0.00 |
| q04 | Do I need a doctor's note for sick leave? | 0.67 | 0.33 | -0.33 |
| q05 | How many days per week can I work from home? | 0.33 | 0.67 | +0.33 |
| q06 | Can I expense a co-working space membership? | 0.67 | 0.67 | +0.00 |
| q07 | What's the home office equipment allowance? | 0.67 | 0.67 | +0.00 |
| q08 | What are the core hours when working remotely? | 0.67 | 0.67 | +0.00 |
| q09 | What's the meal allowance during US business travel? | 0.33 | 0.33 | +0.00 |
| q10 | How long do I have to submit travel receipts? | 0.67 | 0.67 | +0.00 |
| q11 | Can I expense a Notion subscription for myself? | 0.67 | 0.33 | -0.33 |
| q12 | Is there a cap on training expenses? | 0.67 | 0.33 | -0.33 |
| q13 | How do I reset my VPN password? | 1.00 | 1.00 | +0.00 |
| q14 | What's the IT helpdesk number? | 0.67 | 0.33 | -0.33 |
| q15 | Is the VPN available on mobile devices? | 1.00 | 0.67 | -0.33 |
| q16 | What do I do if my laptop is stolen at the airport? | 1.00 | 1.00 | +0.00 |
| q17 | What's the security hotline number for urgent out-of-ho | 0.67 | 0.67 | +0.00 |
| q18 | Will I be punished for reporting a phishing click I mad | 1.00 | 1.00 | +0.00 |
| q19 | How long does it take to get a replacement laptop? | 0.33 | 0.33 | +0.00 |
| q20 | Do I need to use the VPN when working from home? | 0.33 | 0.33 | +0.00 |
