"""Qdrant Vector Database helper client with local fallback support."""

from __future__ import annotations

import os
from typing import Any, List, Optional
from app.core.logger import get_logger

try:
    from qdrant_client import QdrantClient as RealQdrantClient  # type: ignore
    from qdrant_client.models import Distance, VectorParams, PointStruct  # type: ignore
except ImportError:
    RealQdrantClient = None
    Distance = None
    VectorParams = None
    PointStruct = None

logger = get_logger("agentsphere.memory.qdrant")


class QdrantVectorClient:
    """Manages text embeddings search and upserts using Qdrant Vector Store."""

    def __init__(self) -> None:
        self.host = os.getenv("QDRANT_HOST")
        self.api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("QDRANT_COLLECTION", "showrunner_memory")

        self.client = None
        self._fallback_store: dict[str, list[float]] = {}
        self._fallback_payloads: dict[str, dict[str, Any]] = {}

        if RealQdrantClient is not None and self.host:
            try:
                if self.api_key:
                    self.client = RealQdrantClient(url=self.host, api_key=self.api_key)
                else:
                    self.client = RealQdrantClient(url=self.host)
                
                # Check and create collection if not exists
                collections = self.client.get_collections().collections
                exists = any(c.name == self.collection_name for c in collections)
                if not exists:
                    # 1536 is the default dimension for most modern embedding models
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                    )
                logger.info("Qdrant Vector DB Client initialized for collection: %s", self.collection_name)
            except Exception as e:
                logger.warning("Failed to initialize Qdrant client: %s. Using in-memory fallback.", e)
        else:
            logger.info("Qdrant host config missing or SDK uninstalled. Using in-memory fallback storage.")

    def upsert_vector(self, doc_id: str, vector: list[float], payload: dict[str, Any] | None = None) -> bool:
        """Insert or update a document embedding vector and metadata payload."""
        if self.client is not None and PointStruct is not None:
            try:
                # doc_id must be converted to valid numeric or UUID, or string hash
                # Simple string hash to integer for Qdrant ID if not numeric
                import hashlib
                numeric_id = int(hashlib.md5(doc_id.encode()).hexdigest(), 16) % (10 ** 15)
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        PointStruct(
                            id=numeric_id,
                            vector=vector,
                            payload=payload or {}
                        )
                    ]
                )
                logger.info("Successfully upserted vector to Qdrant: %s", doc_id)
                return True
            except Exception as e:
                logger.error("Failed to upsert vector to Qdrant: %s. Saving to fallback.", e)
        
        # Local Fallback
        self._fallback_store[doc_id] = vector
        self._fallback_payloads[doc_id] = payload or {}
        return True

    def search_similar(self, query_vector: list[float], limit: int = 3) -> list[dict[str, Any]]:
        """Search for top K most similar vectors using Cosine similarity."""
        if self.client is not None:
            try:
                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit
                )
                return [
                    {
                        "id": r.id,
                        "score": r.score,
                        "payload": r.payload
                    }
                    for r in results
                ]
            except Exception as e:
                logger.error("Qdrant vector search query failed: %s", e)

        # Fallback Cosine Similarity search over fallback dictionary
        import math
        def dot_product(v1, v2):
            return sum(x * y for x, y in zip(v1, v2))
        
        def magnitude(v):
            return math.sqrt(sum(x * x for x in v))

        matches = []
        for doc_id, vector in self._fallback_store.items():
            mag_query = magnitude(query_vector)
            mag_vec = magnitude(vector)
            if mag_query == 0 or mag_vec == 0:
                score = 0.0
            else:
                score = dot_product(query_vector, vector) / (mag_query * mag_vec)
            
            matches.append({
                "id": doc_id,
                "score": score,
                "payload": self._fallback_payloads[doc_id]
            })

        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:limit]
