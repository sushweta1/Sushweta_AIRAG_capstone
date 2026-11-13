# W9 Retrieval Method Comparison

Compared 3 retrieval methods on the 20-question golden set, k=3.

## Summary

| Method | Hits | Hit rate | Cost | Retrieve p50 | E2E p50/p95 |
|---|---|---|---|---|---|
| dense | 20/20 | 100% | $0.00152 | 41ms | 1842ms / 2702ms |
| hybrid | 20/20 | 100% | $0.00152 | 53ms | 1619ms / 2229ms |
| hybrid_rerank | 20/20 | 100% | $0.00154 | 435ms | 2154ms / 8362ms |

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
| q09 | What's the meal allowance during US business travel? | expense_policy.pdf | ✓ | ✓ | ✓ |
| q10 | How long do I have to submit travel receipts? | expense_policy.pdf | ✓ | ✓ | ✓ |
| q11 | Can I expense a Notion subscription for myself? | expense_policy.pdf | ✓ | ✓ | ✓ |
| q12 | Is there a cap on training expenses? | expense_policy.pdf | ✓ | ✓ | ✓ |
| q13 | How do I reset my VPN password? | vpn_setup.html | ✓ | ✓ | ✓ |
| q14 | What's the IT helpdesk number? | vpn_setup.html | ✓ | ✓ | ✓ |
| q15 | Is the VPN available on mobile devices? | vpn_setup.html | ✓ | ✓ | ✓ |
| q16 | What do I do if my laptop is stolen at the airport? | security_incident.docx | ✓ | ✓ | ✓ |
| q17 | What's the security hotline number for urgent out-of-ho | security_incident.docx | ✓ | ✓ | ✓ |
| q18 | Will I be punished for reporting a phishing click I mad | security_incident.docx | ✓ | ✓ | ✓ |
| q19 | How long does it take to get a replacement laptop? | security_incident.docx | ✓ | ✓ | ✓ |
| q20 | Do I need to use the VPN when working from home? | wfh_policy.md | ✓ | ✓ | ✓ |
