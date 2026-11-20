# Week 10 — Knowledge Lifecycle Operations Runbook

## 1. Purpose

Operate the Week 10 RAG pipeline safely when documents are
updated, superseded, or removed from live retrieval.

This runbook covers:

- Document-update previews
- Controlled document replacement
- Tombstone verification
- Response-cache invalidation
- KB-version verification
- Freshness testing
- Recovery and escalation

## 2. Environment

Repository:
`/voc/work/Sushweta_AIRAG_capstone`

Working directory:
`/voc/work/Sushweta_AIRAG_capstone/week10`

Activate the environment:

```bash
cd /voc/work/Sushweta_AIRAG_capstone/week10
source .venv/bin/activate


```

## 3. Safety rules

1. Use only `capstone_chunks_v10` for Week 10 updates.
2. Never reset older Week 8/9 collections.
3. Preview and review replacement documents before confirming updates.
4. Invalidate cached answers when knowledge changes.
5. Verify tombstones, live chunks, and KB-version advancement.
6. Never reconstruct redacted information to satisfy evaluation answers.

## 4. Document update procedure

1. Confirm the replacement source is complete and approved.
2. Confirm the target collection is `capstone_chunks_v10`.
3. Preview the update using `scripts/update_document.py` without `--confirm`.
4. Review the preview before proceeding.
5. Execute the approved update using `--confirm`.
6. Record the affected source, previous KB version, and new KB version.

Never execute an update solely to improve an evaluation score.

## 5. Post-update verification

Verify that:

- Superseded chunks have a `deleted_at` tombstone.
- Replacement chunks are present and live.
- Dense retrieval excludes tombstoned chunks.
- Hybrid retrieval excludes tombstoned chunks.
- The response cache has been invalidated.
- The persistent KB version has advanced.
- A fresh answer reflects the replacement document.
- An identical repeated question produces an eligible cache hit.

A successful update command is not sufficient evidence of freshness.

## 6. Recovery and rollback

If an update fails:

1. Stop further document updates.
2. Record the error and current KB version.
3. Inspect the affected source's live and tombstoned chunks.
4. Check whether replacement chunks were partially inserted.
5. Verify cache state and KB-version consistency.
6. Review rollback results before taking corrective action.
7. Restore a verified source version using an approved procedure.
8. Retest retrieval and answer freshness.

The implementation attempts rollback but does not provide an
atomic transaction across Qdrant, SQLite, and the KB-version file.

Do not reset the entire collection as an initial recovery action.

## 7. Source integrity and redaction

Before indexing, verify that:

- The original source document is readable.
- Extracted text preserves important facts and complete sentences.
- Chunking does not silently discard information.
- Currency amounts, dates, and approval thresholds remain intact.
- Redaction is applied consistently.
- Source metadata supports traceability.

Known limitation: the indexed `expense_policy.pdf` contains
incomplete passages, and its original PDF was unavailable
during investigation.

Do not reconstruct missing policy facts from golden answers.

Redacted values such as `[PERSON]`, `[EMAIL]`, and `[PHONE]`
must not be inferred or restored merely to improve evaluation results.

## 8. Monitoring and escalation

Monitor retrieval coverage, task success, cache hit rate,
answer consistency, latency, costs, stale-answer incidents,
update failures, and tombstone-filter violations.

Stop and investigate when:

- Deleted evidence appears in live retrieval.
- Cached answers remain stale after an update.
- The KB version fails to advance.
- Replacement content is incomplete.
- Unexpected redacted information appears in an answer.

## 9. Operational completion checklist

- [ ] Replacement source reviewed
- [ ] Update preview reviewed
- [ ] Authorized update completed
- [ ] Old chunks tombstoned
- [ ] Replacement chunks verified live
- [ ] KB version advanced
- [ ] Cache invalidation verified
- [ ] Fresh answer grounded in updated evidence
- [ ] Repeated-query cache behavior verified
- [ ] No stale evidence returned
- [ ] Results and exceptions documented

## 10. Supporting evidence

- `docs/kpi/wk10-snapshot.md`
- `docs/adr/ADR-001-week10-cache-lifecycle.md`
- `results/wk10/summary.json`
- `scripts/update_document.py`
- `scripts/evaluate_w10.py`
