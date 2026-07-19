"""Memory Agent managing memory tiers (Short, Long, Forgotten, Archived) with Qdrant vector retrieval."""

from __future__ import annotations

import os
import json
import sqlite3
import math
from typing import Any, Dict, List, Optional
from app.core.logger import get_logger
from app.memory.qdrant_client import QdrantVectorClient

logger = get_logger("agentsphere.memory.agent")


class MemoryAgent:
    """Memory Agent: Orchestrates short-term, long-term, archived, and forgotten memories."""

    def __init__(self, db_path: str = "checkpoints.sqlite") -> None:
        self.db_path = db_path
        self.qdrant = QdrantVectorClient()
        self._init_sqlite()

    def _init_sqlite(self) -> None:
        """Initialize local SQLite store for long-term / archived memory fallbacks."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_memories (
                id TEXT PRIMARY KEY,
                tier TEXT,
                content TEXT,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()

    def store_memory(self, content: str, tier: str = "long_term", metadata: dict | None = None) -> None:
        """Store a memory item in a specific ranking tier (short_term, long_term, archived, forgotten)."""
        logger.info(f"Storing memory in tier '{tier}': {content[:50]}...")
        doc_id = f"mem_{tier}_{hash(content) % 100000}"
        
        # If long term, save to Qdrant vector database (using a mock embedding representation)
        if tier in ["long_term", "archived"]:
            # Basic dummy embedding dimension of 1536 for semantic searches
            dummy_vector = [0.15] * 1536
            # Set indices based on keywords
            if "anime" in content.lower():
                dummy_vector[0] = 0.95
            elif "marvel" in content.lower() or "superhero" in content.lower():
                dummy_vector[1] = 0.95
            elif "dark" in content.lower():
                dummy_vector[2] = 0.95
            
            self.qdrant.upsert_vector(
                doc_id=doc_id,
                vector=dummy_vector,
                payload={"content": content, "tier": tier, "metadata": metadata or {}}
            )

        # Always persist locally to SQLite database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_memories (id, tier, content, metadata) VALUES (?, ?, ?, ?)",
            (doc_id, tier, content, json.dumps(metadata or {}))
        )
        conn.commit()
        conn.close()

    def recall_memories(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Recall relevant memories matching the query semantic meaning."""
        logger.info(f"Recalling memories for query: {query}")
        
        # Build query vector
        query_vector = [0.15] * 1536
        if "anime" in query.lower():
            query_vector[0] = 0.95
        if "marvel" in query.lower() or "superhero" in query.lower():
            query_vector[1] = 0.95
        if "dark" in query.lower():
            query_vector[2] = 0.95

        # Query Qdrant vector client
        results = self.qdrant.search_similar(query_vector, limit=limit)
        
        recalled = []
        for r in results:
            payload = r.get("payload") or {}
            if payload:
                recalled.append({
                    "id": r.get("id"),
                    "score": r.get("score"),
                    "content": payload.get("content"),
                    "tier": payload.get("tier"),
                    "metadata": payload.get("metadata")
                })
        
        # If Qdrant returns nothing, query SQLite as local fallback
        if not recalled:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, tier, content, metadata FROM user_memories")
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                content = row[2]
                # Simple keyword matching fallback
                if any(word in content.lower() for word in query.lower().split()):
                    recalled.append({
                        "id": row[0],
                        "score": 0.85,
                        "content": content,
                        "tier": row[1],
                        "metadata": json.loads(row[3])
                    })
        
        return recalled[:limit]
