# W9 Retrieval Method Comparison

Compared 3 retrieval methods on the 20-question golden set, k=3.

## Summary

| Method | Hits | Hit rate | Cost | Retrieve p50 | E2E p50/p95 |
|---|---|---|---|---|---|
| dense | 9/20 | 45% | $0.00151 | 40ms | 2638ms / 4317ms |
| hybrid | 9/20 | 45% | $0.00151 | 50ms | 1678ms / 2774ms |
| hybrid_rerank | 9/20 | 45% | $0.00154 | 442ms | 2485ms / 5419ms |

## Per-question results

| Q | Question | Expected source | dense | hybrid | hybrid_rerank |
|---|---|---|---|---|---|
| q01 | How many days of paid annual leave do I get? | leave_policy.md | ✓ | ✓ | ✓ |
| q02 | Can I carry over unused leave to next year? | leave_policy.md | ✓ | ✓ | ✓ |
| q03 | How much parental leave is available? | leave_policy.md | ✓ | ✓ | ✓ |
| q04 | Do I need a doctor's note for sick leave? | leave_policy.md | ✓ | ✓ | ✓ |
| q05 | How many days per week can I work from home? | wfh_policy.md | ✓ | ✓ | ✓ |
| q06 | Can I expense a co-working space membership? | wfh_policy.md | ✓ | ✓ | ✓ |
| q07 | What's the home office equipment allowance? | wfh_policy.md | ✓ | ✓ | ✓ |
| q08 | What are the core hours when working remotely? | wfh_policy.md | ✓ | ✓ | ✓ |
| q09 | What's the meal allowance during US business travel? | expense_policy.md | ✗ | ✗ | ✗ |
| q10 | How long do I have to submit travel receipts? | expense_policy.md | ✗ | ✗ | ✗ |
| q11 | Can I expense a Notion subscription for myself? | expense_policy.md | ✗ | ✗ | ✗ |
| q12 | Is there a cap on training expenses? | expense_policy.md | ✗ | ✗ | ✗ |
| q13 | How do I reset my VPN password? | vpn_setup.md | ✗ | ✗ | ✗ |
| q14 | What's the IT helpdesk number? | vpn_setup.md | ✗ | ✗ | ✗ |
| q15 | Is the VPN available on mobile devices? | vpn_setup.md | ✗ | ✗ | ✗ |
| q16 | What do I do if my laptop is stolen at the airport? | security_incident.md | ✗ | ✗ | ✗ |
| q17 | What's the security hotline number for urgent out-of-ho | security_incident.md | ✗ | ✗ | ✗ |
| q18 | Will I be punished for reporting a phishing click I mad | security_incident.md | ✗ | ✗ | ✗ |
| q19 | How long does it take to get a replacement laptop? | security_incident.md | ✗ | ✗ | ✗ |
| q20 | Do I need to use the VPN when working from home? | wfh_policy.md | ✓ | ✓ | ✓ |
