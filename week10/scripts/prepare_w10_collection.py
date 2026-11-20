"""Create an isolated Week 10 collection from the redacted baseline."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from src.ingest.pipeline import PAYLOAD_INDEX_FIELDS
import os

load_dotenv(ROOT / ".env")

SOURCE = "capstone_chunks_v2_redacted"
TARGET = "capstone_chunks_v10"

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=60,
)

existing = {
    c.name for c in client.get_collections().collections
}

if SOURCE not in existing:
    raise RuntimeError(f"Source collection missing: {SOURCE}")

if TARGET in existing:
    raise RuntimeError(
        f"{TARGET} already exists. Refusing to overwrite."
    )

source_info = client.get_collection(SOURCE)
config = source_info.config.params.vectors

assert config.size == 1536
assert config.distance == qm.Distance.COSINE

source_count = client.count(
    collection_name=SOURCE,
    exact=True,
).count

print(f"Source collection: {SOURCE}")
print(f"Source points: {source_count}")

# Create a new collection; never delete existing collections.
client.create_collection(
    collection_name=TARGET,
    vectors_config=qm.VectorParams(
        size=config.size,
        distance=config.distance,
    ),
)

print(f"Created: {TARGET}")

schema_map = {
    "keyword": qm.PayloadSchemaType.KEYWORD,
    "integer": qm.PayloadSchemaType.INTEGER,
    "float": qm.PayloadSchemaType.FLOAT,
    "bool": qm.PayloadSchemaType.BOOL,
    "text": qm.PayloadSchemaType.TEXT,
}

# Preserve existing indexes and add lifecycle indexes.
index_fields = PAYLOAD_INDEX_FIELDS + [
    ("deleted_at", "float"),
    ("kb_version", "keyword"),
]

for field, schema in index_fields:
    client.create_payload_index(
        collection_name=TARGET,
        field_name=field,
        field_schema=schema_map[schema],
        wait=True,
    )
    print(f"  Indexed: {field}")

offset = None
copied = 0

while True:
    points, next_offset = client.scroll(
        collection_name=SOURCE,
        limit=64,
        offset=offset,
        with_payload=True,
        with_vectors=True,
    )

    batch = []

    for point in points:
        payload = dict(point.payload or {})

        assert payload.get("embedding_model") == \
            "text-embedding-3-small"

        payload["kb_version"] = "v2.w10"

        batch.append(
            qm.PointStruct(
                id=point.id,
                vector=point.vector,
                payload=payload,
            )
        )

    if batch:
        client.upsert(
            collection_name=TARGET,
            points=batch,
            wait=True,
        )
        copied += len(batch)

    if next_offset is None:
        break

    offset = next_offset

target_count = client.count(
    collection_name=TARGET,
    exact=True,
).count

live_filter = qm.Filter(
    must=[
        qm.IsEmptyCondition(
            is_empty=qm.PayloadField(key="deleted_at")
        )
    ]
)

live_count = client.count(
    collection_name=TARGET,
    count_filter=live_filter,
    exact=True,
).count

source_after = client.count(
    collection_name=SOURCE,
    exact=True,
).count

print("\n--- VERIFICATION ---")
print("Source before:", source_count)
print("Source after: ", source_after)
print("Copied:       ", copied)
print("Target total: ", target_count)
print("Target live:  ", live_count)

assert copied == target_count == source_count
assert source_after == source_count
assert live_count == target_count

print("\nSUCCESS: Week 10 collection ready.")
print("No existing collections were overwritten.")
