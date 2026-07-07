"""Chunk the coaching corpus, embed with FastEmbed, and upsert into Qdrant.

Reads every markdown file under backend/knowledge/corpus/, parses its `---`
frontmatter into retrieval metadata, splits the body into section-sized chunks,
embeds each chunk locally with FastEmbed, and upserts them into the
`coaching_knowledge` collection.

Usage (from backend/):
    python -m rag.ingest_knowledge            # create-if-missing, then upsert
    python -m rag.ingest_knowledge --recreate # drop & recreate the collection first
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import uuid

from fastembed import TextEmbedding, SparseTextEmbedding
from qdrant_client import QdrantClient, models

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config
from rag.setup_collection import create_coaching_collection

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge", "corpus")
COLLECTION = "coaching_knowledge"
_NS = uuid.uuid5(uuid.NAMESPACE_URL, "onetapai-knowledge")

# Metadata keys mirrored into the Qdrant payload for pre-filtering.
_META_KEYS = ("agent", "map", "role", "rank_range", "concept_type", "title", "source")


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split leading `--- ... ---` key:value frontmatter from the markdown body."""
    meta: dict = {}
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
        return meta, body.strip()
    return meta, text.strip()


def _chunk_by_section(body: str) -> list[str]:
    """Split on `## ` headings; each heading + its prose becomes one chunk."""
    chunks: list[str] = []
    current: list[str] = []
    for line in body.splitlines():
        if line.startswith("## ") and current:
            chunks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current).strip())
    return [c for c in chunks if c]


def load_chunks() -> list[dict]:
    """Return [{content, metadata, source}] for every chunk in the corpus."""
    records: list[dict] = []
    for path in sorted(glob.glob(os.path.join(CORPUS_DIR, "*.md"))):
        with open(path, encoding="utf-8") as f:
            meta, body = _parse_frontmatter(f.read())
        source = meta.get("source") or os.path.basename(path)
        metadata = {k: meta[k] for k in _META_KEYS if k in meta}
        for section in _chunk_by_section(body):
            # Prepend the doc title so a standalone chunk keeps its context.
            content = f"{meta.get('title', '')}\n\n{section}".strip()
            records.append({"content": content, "metadata": metadata, "source": source})
    return records


def main() -> None:
    ap = argparse.ArgumentParser(description="Embed the coaching corpus into Qdrant.")
    ap.add_argument("--recreate", action="store_true", help="drop & recreate the collection")
    args = ap.parse_args()

    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)

    if args.recreate and client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    if not client.collection_exists(COLLECTION):
        create_coaching_collection(client)
        print(f"Created collection {COLLECTION} (dim={config.EMBEDDING_DIM}).")

    records = load_chunks()
    if not records:
        print(f"No corpus files found in {CORPUS_DIR}.")
        return
    texts = [r["content"] for r in records]
    print(f"Embedding {len(records)} chunks (dense: {config.EMBEDDING_MODEL}, "
          f"sparse: {config.SPARSE_EMBEDDING_MODEL})…")

    dense_vecs = list(TextEmbedding(model_name=config.EMBEDDING_MODEL).embed(texts))
    sparse_vecs = list(SparseTextEmbedding(model_name=config.SPARSE_EMBEDDING_MODEL).embed(texts))

    points = [
        models.PointStruct(
            id=str(uuid.uuid5(_NS, f"{r['source']}:{i}")),
            vector={
                "dense": dv.tolist(),
                "sparse": models.SparseVector(
                    indices=sv.indices.tolist(), values=sv.values.tolist()
                ),
            },
            payload={"content": r["content"], "metadata": r["metadata"], "source": r["source"]},
        )
        for i, (r, dv, sv) in enumerate(zip(records, dense_vecs, sparse_vecs))
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"Upserted {len(points)} chunks into {COLLECTION}.")


if __name__ == "__main__":
    main()
