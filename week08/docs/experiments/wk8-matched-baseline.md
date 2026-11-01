# W7 vs W8 — Collection Comparison

Ran 20 golden questions against both collections with the same embedding model (text-embedding-3-small).

## Summary

| Metric | W7 capstone_chunks_w7_baseline | W8 capstone_chunks_v2_redacted | Δ |
|---|---|---|---|
| Hit rate | 20/20 (100%) | 20/20 (100%) | +0 |
| Cost (total) | $0.00185 | $0.00152 | $-0.00034 |
| Latency p50 | 1143ms | 1172ms | +29ms |
| Latency p95 | 1809ms | 1530ms | -279ms |

## Per-question diff

| Q | Question | W7 got | W8 got | W7 hit | W8 hit |
|---|---|---|---|---|---|
| q01 | How many days of paid annual leave do I get? | leave_policy.md | leave_policy.md | ✓ | ✓ |
| q02 | Can I carry over unused leave to next year? | leave_policy.md | leave_policy.md | ✓ | ✓ |
| q03 | How much parental leave is available? | parental_leave_handbook.md | leave_policy.md | ✓ | ✓ |
| q04 | Do I need a doctor's note for sick leave? | leave_policy.md | leave_policy.md | ✓ | ✓ |
| q05 | How many days per week can I work from home? | wfh_policy.md | wfh_policy.md | ✓ | ✓ |
| q06 | Can I expense a co-working space membership? | wfh_policy.md | wfh_policy.md | ✓ | ✓ |
| q07 | What's the home office equipment allowance? | wfh_policy.md | wfh_policy.md | ✓ | ✓ |
| q08 | What are the core hours when working remotely? | wfh_policy.md | wfh_policy.md | ✓ | ✓ |
| q09 | What's the meal allowance during US business travel? | expense_policy.pdf | expense_policy.pdf | ✓ | ✓ |
| q10 | How long do I have to submit travel receipts? | expense_policy.pdf | expense_policy.pdf | ✓ | ✓ |
| q11 | Can I expense a Notion subscription for myself? | expense_policy.pdf | expense_policy.pdf | ✓ | ✓ |
| q12 | Is there a cap on training expenses? | expense_policy.pdf | expense_policy.pdf | ✓ | ✓ |
| q13 | How do I reset my VPN password? | vpn_setup.html | vpn_setup.html | ✓ | ✓ |
| q14 | What's the IT helpdesk number? | vpn_setup.html | vpn_setup.html | ✓ | ✓ |
| q15 | Is the VPN available on mobile devices? | vpn_setup.html | vpn_setup.html | ✓ | ✓ |
| q16 | What do I do if my laptop is stolen at the airport? | security_incident.docx | security_incident.docx | ✓ | ✓ |
| q17 | What's the security hotline number for urgent out-of-hours i | security_incident.docx | security_incident.docx | ✓ | ✓ |
| q18 | Will I be punished for reporting a phishing click I made? | security_incident.docx | security_incident.docx | ✓ | ✓ |
| q19 | How long does it take to get a replacement laptop? | security_incident.docx | security_incident.docx | ✓ | ✓ |
| q20 | Do I need to use the VPN when working from home? | vpn_setup.html | vpn_setup.html | ✓ | ✓ |

## Evaluation Notes and Limitations

### Matched comparison
- Both collections use the same seven HR/IT source documents.
- Both use text-embedding-3-small.
- Week 7 baseline: fixed-window chunking, 16 chunks.
- Week 8 enhanced: structure-aware chunking, 24 chunks.
- Both were evaluated against the same 20-question golden set.
- The original comparison against capstone_chunks was invalid because
  that collection contained a different corpus.

### Retrieval quality
- Both pipelines achieved 20/20 source hits.
- For q03 (parental leave), the top retrieved source differed between
  pipelines: parental_leave_handbook.md versus leave_policy.md.
- Both were accepted by the current source-hit evaluation.
- Source-hit accuracy does not establish answer correctness,
  faithfulness, or evidence completeness.

### Performance
- Week 8 showed lower estimated cost and lower p95 latency in the
  latest evaluation run.
- Week 8 had slightly higher p50 latency in that run.
- Repeated measurements are needed before drawing conclusions
  about consistent latency improvements.

### Privacy evaluation
- Regex-based redaction covers selected email, phone, and identifier
  patterns.
- Known-person-name redaction was expanded after manual review.
- The original review identified additional unmasked names and an
  email address with a single-label domain.
- All seven specifically checked identifiers were absent from the
  regenerated local review file.
- Manual review was completed before ingestion.
- Redaction remains rule-based and is not comprehensive named-entity
  recognition; unidentified personal information may still remain.
- Previously ingested collections were preserved rather than deleted.
