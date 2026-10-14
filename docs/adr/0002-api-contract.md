```

Response:

Streaming plain text response.

The `/ask` endpoint uses the Week 2 pipeline internally and streams the generated answer word-by-word.

### POST `/ask_batched`

Request:

```json
{
  "question": "What is RAG?"
}
```

Response:

```json
{
  "content": "RAG combines retrieval with generation.",
  "cost_usd": 0.0,
  "retries": 0
}
```

### GET `/health`

Response:

```json
{
  "status": "ok"
}
```

## Public Models

### Question

- `question: str`

### Answer

- `content: str`
- `cost_usd: float`
- `retries: int`

## Internal Mapping

The Week 3 API translates between the public API models and the Week 2 internal pipeline models.

- Public `question` maps to the Week 2 internal `text` field.
- Week 2 answer `text` maps to the public `content` field.

This keeps the external API contract independent of the internal pipeline representation.

## Persistence

Successful `/ask` requests are persisted using the Week 2 SQLite persistence layer in `src/pipeline/store.py`.

Each successful request creates:

- one row in `runs`
- one corresponding row in `answers`

`answers.run_id` is linked to `runs.id` through a foreign key.

The persistence layer was tested with 50 requests at up to 10 concurrent requests. All 50 requests succeeded and all 50 were persisted.

## Consequences

- Clients depend on a stable Week 3 API contract.
- Internal pipeline implementation can evolve without changing the public field names.
- FastAPI/Pydantic validates incoming requests.
- `/ask` provides streaming output while `/ask_batched` provides a normal JSON response.
- The existing Week 2 SQLite persistence layer is reused for successful `/ask` requests.

## Week 4 Update

Week 4 preserves the existing public API contract while evolving the internal
implementation.

The following endpoints remain unchanged:

- `POST /ask`
- `POST /ask_batched`
- `GET /health`

The `Question` request model remains:

- `question: str`

The existing `Answer` fields remain:

- `content: str`
- `cost_usd: float`
- `retries: int`

Week 4 adds the following optional response fields:

- `confidence: float`
- `sources: list[str]`
- `schema_version: str`

These are additive changes, so the public API remains version `v1`.

### Schema Versioning Rule

Every `Answer` response carries a `schema_version` field. The current schema
version is `v1`. Backward-compatible additive changes do not require a
`schema_version` bump.

Examples of changes that remain within `v1` include:

- adding optional response fields
- adding new endpoints
- changing retry or streaming implementation internally
- changing the model used behind the API

Breaking changes require a new schema version such as `v2`, `v3`, and so on.

Breaking changes include:

- removing an existing field
- renaming an existing field
- changing the type of an existing field
- changing an optional field to required
- changing the meaning or semantics of an existing field
- changing the API error response shape in a way that breaks existing clients

When a new schema version is introduced, the existing version remains the
default initially. Clients may opt into the new version using an
`X-Schema-Version` header or a `schema_version` query parameter.

The old and new schema versions should be supported in parallel for at least
two weeks before the older version is retired.

### Cost Budget

Capstone `/ask_batched` calls should cost no more than $0.002 per answer on
average over the comparison batch.

In the Week 4 comparison, `gpt-4o-mini` averaged approximately $0.000079 per
question, while `gpt-4o` averaged approximately $0.001516 per question.

### Chosen Default Model

The default `Settings.model` is `gpt-4o-mini`.

The Step 3 comparison showed that `gpt-4o-mini` completed the same 10-question
test set at approximately 19.2 times lower cost than `gpt-4o`, with no
consistent quality advantage from the larger model.

`gpt-4o` may still be used for tasks where a measured improvement in answer
quality justifies the additional cost and latency.

### Persistence Update

Week 4 extends the SQLite `answers` schema with:

- `model`
- `confidence`
- `sources_json`
- `schema_version`

The migration is idempotent, so running the migration repeatedly does not
re-add existing columns.

`POST /ask_batched` persists the structured answer together with the model,
real API cost, confidence, sources, and schema version.

### Consequences

- Existing Week 3 clients continue to work without changes.
- The API can evolve internally without requiring a new public version for
  additive changes.
- Real token usage is converted into `cost_usd`.
- Model cost can be compared and used as an engineering decision criterion.
- Schema versioning provides an explicit boundary between compatible and
  breaking API changes.