import os
import sys

from qdrant_client import QdrantClient, models

# Make the shared `config` module importable regardless of working directory
# (temporary shim until the backend is packaged with __init__.py files).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

def create_coaching_collection(client: QdrantClient):
    # Named vectors enable hybrid search: a dense semantic vector plus a sparse
    # BM25 lexical vector, fused with Reciprocal Rank Fusion at query time.
    client.create_collection(
        collection_name="coaching_knowledge",
        vectors_config={
            "dense": models.VectorParams(
                size=config.EMBEDDING_DIM,  # must match config.EMBEDDING_MODEL
                distance=models.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            # IDF modifier turns raw term weights into BM25-style scoring.
            "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF),
        },
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=10000,
        ),
    )

    # Create payload indexes for fast filtering
    for field_name, field_type in [
        ("agent", models.PayloadSchemaType.KEYWORD),
        ("map", models.PayloadSchemaType.KEYWORD),
        ("role", models.PayloadSchemaType.KEYWORD),      # duelist, controller, etc.
        ("rank_range", models.PayloadSchemaType.KEYWORD), # iron-bronze, silver-gold, etc.
        ("concept_type", models.PayloadSchemaType.KEYWORD),
        ("source", models.PayloadSchemaType.KEYWORD),
    ]:
        client.create_payload_index(
            collection_name="coaching_knowledge",
            field_name=field_name,
            field_schema=field_type,
        )
