import os
import sys
from dataclasses import dataclass, field
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from fastembed import TextEmbedding, SparseTextEmbedding

# Make the shared `config` module importable regardless of working directory
# (temporary shim until the backend is packaged with __init__.py files).
# Aliased to `app_config` because the RetrievalConfig parameter below is
# conventionally named `config` and would otherwise shadow this module.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config as app_config

@dataclass
class RetrievalConfig:
    collection_name: str = "coaching_knowledge"
    top_k: int = 8
    prefetch_limit: int = 20   # candidates per arm (dense/sparse) before RRF fusion

@dataclass
class RetrievedChunk:
    content: str
    metadata: dict
    score: float
    source: str

class CoachingRetriever:
    # Cache the embedding models at class level — loading them is expensive and
    # they are stateless, so single instances are safely shared across retrievers.
    _dense: TextEmbedding | None = None
    _sparse: SparseTextEmbedding | None = None

    def __init__(self, qdrant: QdrantClient, config: RetrievalConfig):
        self.qdrant = qdrant
        self.config = config
        if CoachingRetriever._dense is None:
            CoachingRetriever._dense = TextEmbedding(model_name=app_config.EMBEDDING_MODEL)
        if CoachingRetriever._sparse is None:
            CoachingRetriever._sparse = SparseTextEmbedding(
                model_name=app_config.SPARSE_EMBEDDING_MODEL
            )
        self.dense = CoachingRetriever._dense
        self.sparse = CoachingRetriever._sparse

    @classmethod
    def from_config(cls) -> "CoachingRetriever":
        """Build a retriever with a Qdrant client from the shared config/.env."""
        client = QdrantClient(
            host=app_config.QDRANT_HOST,
            port=app_config.QDRANT_PORT,
            api_key=app_config.QDRANT_API_KEY,  # None in dev; required when set
            https=app_config.QDRANT_HTTPS,
            check_compatibility=False,  # silence client/server minor-version skew warning
        )
        return cls(client, RetrievalConfig())

    def _embed_dense(self, text: str) -> list[float]:
        return next(iter(self.dense.embed([text]))).tolist()

    def _embed_sparse(self, text: str) -> models.SparseVector:
        sv = next(iter(self.sparse.embed([text])))
        return models.SparseVector(indices=sv.indices.tolist(), values=sv.values.tolist())

    def retrieve(
        self,
        query: str,
        filters: dict | None = None,
    ) -> list[RetrievedChunk]:
        """Hybrid retrieval: dense semantic + sparse BM25 arms fused with
        Reciprocal Rank Fusion (RRF). Runs entirely locally via FastEmbed."""
        # Build Qdrant filter from metadata
        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
                if v is not None
            ]
            if conditions:
                qdrant_filter = Filter(must=conditions)

        response = self.qdrant.query_points(
            collection_name=self.config.collection_name,
            prefetch=[
                models.Prefetch(
                    query=self._embed_dense(query),
                    using="dense",
                    limit=self.config.prefetch_limit,
                    filter=qdrant_filter,
                ),
                models.Prefetch(
                    query=self._embed_sparse(query),
                    using="sparse",
                    limit=self.config.prefetch_limit,
                    filter=qdrant_filter,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=self.config.top_k,
            with_payload=True,
        )

        return [
            RetrievedChunk(
                content=hit.payload["content"],
                metadata=hit.payload.get("metadata", {}),
                score=hit.score,
                source=hit.payload.get("source", "unknown"),
            )
            for hit in response.points
        ]

    def multi_query_retrieve(
        self,
        player_profile: dict,
    ) -> list[RetrievedChunk]:
        """
        Decompose player profile into multiple targeted queries.
        """
        queries = []

        # Mechanical queries
        for deficiency in player_profile.get("aim_deficiencies", []):
            queries.append({
                "query": f"How to fix {deficiency} in Valorant aiming mechanics",
                "filters": {"concept_type": "mechanical"},
            })

        # Agent-specific queries
        agent = player_profile.get("main_agent")
        if agent:
            queries.append({
                "query": f"Advanced {agent} positioning and ability usage guide",
                "filters": {"agent": agent},
            })

        # Map-specific queries
        worst_map = player_profile.get("worst_map")
        if worst_map:
            queries.append({
                "query": f"Defensive and offensive strategies for {worst_map}",
                "filters": {"map": worst_map},
            })

        # Positioning queries (if spatial analysis flagged issues)
        peek_issues = player_profile.get("peek_issues", [])
        if "wide_swing" in peek_issues:
            queries.append({
                "query": "How to stop wide swinging and use tight peeks in Valorant",
                "filters": {"concept_type": "positioning"},
            })

        # Mental game queries
        if player_profile.get("tilt_probability", 0) > 0.4:
            queries.append({
                "query": "Mental reset techniques and tilt management for competitive FPS",
                "filters": {"concept_type": "mental"},
            })

        # Execute all queries and deduplicate
        all_chunks = []
        seen_contents = set()
        for q in queries:
            chunks = self.retrieve(q["query"], q.get("filters"))
            for chunk in chunks:
                content_hash = hash(chunk.content[:200])
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    all_chunks.append(chunk)

        # Sort by relevance score and return top-K
        all_chunks.sort(key=lambda c: c.score, reverse=True)
        return all_chunks[: self.config.top_k]
