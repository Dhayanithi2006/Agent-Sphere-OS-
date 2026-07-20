"""Hybrid shared memory coordinator supporting SQLite, Redis, locking, transactions and vector queries."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import redis

from app.core.config import settings as default_settings
from app.core.logging import get_logger

logger = get_logger("agentsphere.memory_manager")


class InMemoryConnection(sqlite3.Connection):
    """Subclass of sqlite3.Connection overriding close() as a no-op for cached connections."""

    def close(self) -> None:
        pass


class MemoryManager:
    """Consolidated Memory Manager coordinating multiple storage engines and vector memory."""

    def __init__(self, db_path: Optional[str] = None, redis_url: Optional[str] = None) -> None:
        self._db_path = db_path or default_settings.database_path
        self._redis_url = redis_url or default_settings.redis_url
        self._redis_client: Optional[redis.Redis] = None
        self._connection: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()
        # Thread-level lock to protect SQLite from concurrent thread access
        # (asyncio.Lock only works in async coroutines, not in asyncio.to_thread sync workers)
        self._thread_lock = threading.RLock()
        
        # Transaction buffer mapping tx_id -> dict(storage_key -> serialized_value)
        self._active_transactions: Dict[str, Dict[str, str]] = {}
        
        # Lock registry mapping lock_key -> (owner_id, expiration_timestamp)
        self._locks: Dict[str, tuple[str, float]] = {}

        self._ensure_parent_directory()
        self._ensure_schema()
        self._init_redis()

    def _ensure_parent_directory(self) -> None:
        if self._db_path == ":memory:":
            return
        parent = os.path.dirname(self._db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def _ensure_schema(self) -> None:
        connection = self._connect()
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_items (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                version INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS vector_items (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                vector TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
            """
        )
        connection.commit()

    def _connect(self) -> sqlite3.Connection:
        """Return a cached SQLite connection, creating it on first call.

        For both :memory: and file-based databases we keep a single long-lived
        connection protected by _thread_lock.  Creating a new connection on
        every call and closing it in a finally-block caused
        ``InterfaceError: bad parameter or other API misuse`` when concurrent
        asyncio tasks (e.g. asyncio.gather) raced to close/use the same handle.
        """
        if self._connection is not None:
            return self._connection

        if self._db_path == ":memory:":
            connection = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                isolation_level=None,
                factory=InMemoryConnection
            )
        else:
            connection = sqlite3.connect(self._db_path, check_same_thread=False, isolation_level=None)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=5000")

        connection.row_factory = sqlite3.Row
        self._connection = connection
        return connection

    def reset_for_test(self, db_path: str = ":memory:") -> None:
        """Atomically swap the database path and connection for test isolation.

        This replaces the unsafe conftest.py pattern of:
            obj._connection = None   # ← race: background tasks still use old cursor
            obj._db_path = ":memory:"
            obj._ensure_schema()

        By holding _thread_lock (an RLock) throughout the entire swap we
        guarantee no concurrent coroutine observes a partially-reset state.
        _ensure_schema() re-acquires the same RLock internally — that is safe
        because RLock allows the same thread to acquire it multiple times.
        """
        with self._thread_lock:
            old_conn = self._connection
            self._connection = None
            self._db_path = db_path
            # Re-initialise schema on the new connection (safe: RLock is re-entrant)
            self._ensure_schema()
            # Close the old connection AFTER the new one is ready.
            # Call the base-class close() directly to bypass InMemoryConnection.close()
            # which is a no-op, so the underlying file handle is actually released.
            if old_conn is not None:
                try:
                    sqlite3.Connection.close(old_conn)
                except Exception:
                    pass






    def _init_redis(self) -> None:
        if self._redis_url:
            try:
                self._redis_client = redis.from_url(self._redis_url, decode_responses=True)
                # Quick test connection
                self._redis_client.ping()
                logger.info("Connected to Redis shared memory backend")
            except Exception as exc:
                logger.warning(f"Redis initialization failed (falling back to SQLite): {exc}")
                self._redis_client = None

    @staticmethod
    def _compose_key(namespace: Optional[str], key: str) -> str:
        return f"{namespace}:{key}" if namespace else key

    # ---------------------------------------------------------------------------
    # CRUD Operations
    # ---------------------------------------------------------------------------

    def write(self, namespace: Optional[str], key: str, value: Any, tx_id: Optional[str] = None) -> None:
        """Write key-value data to memory, supporting transaction buffering."""
        storage_key = self._compose_key(namespace, key)
        serialized = json.dumps(value, sort_keys=True)

        if tx_id:
            # Buffer transaction writes
            if tx_id not in self._active_transactions:
                raise ValueError(f"Transaction ID '{tx_id}' does not exist")
            self._active_transactions[tx_id][storage_key] = serialized
            logger.info(f"Buffered write to transaction '{tx_id}' for key '{storage_key}'")
            return

        # Direct write path (not transactional)
        self._persist_key(storage_key, serialized)

    def read(self, namespace: Optional[str], key: str, default: Any = None) -> Any:
        """Retrieve key-value data from memory."""
        storage_key = self._compose_key(namespace, key)
        
        # Check Redis first if available
        if self._redis_client:
            try:
                val = self._redis_client.get(storage_key)
                if val is not None:
                    return json.loads(val)
            except Exception:
                pass

        # Fallback to SQLite
        with self._thread_lock:
            connection = self._connect()
            row = connection.execute("SELECT value FROM memory_items WHERE key = ?", (storage_key,)).fetchone()
            if row is None:
                return default
            return json.loads(row["value"])

    def exists(self, namespace: Optional[str], key: str) -> bool:
        """Check if key exists in memory."""
        storage_key = self._compose_key(namespace, key)
        if self._redis_client:
            try:
                if self._redis_client.exists(storage_key):
                    return True
            except Exception:
                pass

        with self._thread_lock:
            connection = self._connect()
            row = connection.execute("SELECT 1 FROM memory_items WHERE key = ?", (storage_key,)).fetchone()
            return row is not None

    def delete(self, namespace: Optional[str], key: str) -> None:
        """Delete key and its version history."""
        storage_key = self._compose_key(namespace, key)
        
        if self._redis_client:
            try:
                self._redis_client.delete(storage_key)
                self._redis_client.delete(f"{storage_key}:history")
            except Exception:
                pass

        with self._thread_lock:
            connection = self._connect()
            connection.execute("DELETE FROM memory_items WHERE key = ?", (storage_key,))
            connection.execute("DELETE FROM memory_versions WHERE key = ?", (storage_key,))
            connection.commit()

    def _persist_key(self, storage_key: str, serialized_value: str) -> None:
        """Persist serialized value to SQLite/Redis and create a new version."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Persist to Redis if available
        if self._redis_client:
            try:
                self._redis_client.set(storage_key, serialized_value)
                self._redis_client.rpush(f"{storage_key}:history", serialized_value)
            except Exception:
                pass

        # Persist to SQLite (serialized by thread lock to prevent concurrent write races)
        with self._thread_lock:
            connection = self._connect()
            connection.execute(
                "INSERT INTO memory_items(key, value, updated_at) VALUES(?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (storage_key, serialized_value, now),
            )
            # Fetch next version integer
            latest = connection.execute(
                "SELECT MAX(version) AS version FROM memory_versions WHERE key = ?", (storage_key,)
            ).fetchone()
            version = 1 if latest is None or latest["version"] is None else int(latest["version"]) + 1

            connection.execute(
                "INSERT INTO memory_versions(key, value, version, created_at) VALUES(?, ?, ?, ?)",
                (storage_key, serialized_value, version, now),
            )
            connection.commit()

    # ---------------------------------------------------------------------------
    # Transactions
    # ---------------------------------------------------------------------------

    def begin_transaction(self) -> str:
        """Create a new transaction space and return its ID."""
        tx_id = f"tx-{hashlib.md5(os.urandom(16)).hexdigest()[:8]}"
        self._active_transactions[tx_id] = {}
        logger.info(f"Transaction '{tx_id}' initialized")
        return tx_id

    def commit_transaction(self, tx_id: str) -> None:
        """Commit all buffered changes inside a transaction."""
        if tx_id not in self._active_transactions:
            raise ValueError(f"Invalid transaction ID '{tx_id}'")

        buffered = self._active_transactions.pop(tx_id)
        for storage_key, serialized_val in buffered.items():
            self._persist_key(storage_key, serialized_val)
        
        logger.info(f"Transaction '{tx_id}' committed successfully")

    def rollback_transaction(self, tx_id: str) -> None:
        """Discard all buffered changes inside a transaction."""
        if tx_id not in self._active_transactions:
            raise ValueError(f"Invalid transaction ID '{tx_id}'")

        self._active_transactions.pop(tx_id)
        logger.info(f"Transaction '{tx_id}' rolled back")

    # ---------------------------------------------------------------------------
    # Versioning & Rollback
    # ---------------------------------------------------------------------------

    def history(self, namespace: Optional[str], key: str) -> List[Dict[str, Any]]:
        """Retrieve version logs for a key."""
        storage_key = self._compose_key(namespace, key)
        with self._thread_lock:
            connection = self._connect()
            rows = connection.execute(
                "SELECT value, version, created_at FROM memory_versions WHERE key = ? ORDER BY version ASC",
                (storage_key,),
            ).fetchall()
            return [
                {
                    "value": json.loads(row["value"]),
                    "version": row["version"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def rollback_key_to_version(self, namespace: Optional[str], key: str, version: int) -> bool:
        """Rollback key value to a specific older version index."""
        storage_key = self._compose_key(namespace, key)
        with self._thread_lock:
            connection = self._connect()
            row = connection.execute(
                "SELECT value FROM memory_versions WHERE key = ? AND version = ?", (storage_key, version)
            ).fetchone()
            if not row:
                return False
            # Write back older version value
            serialized = row["value"]
        # Persist outside the lock to allow _persist_key's own lock acquisition
        self._persist_key(storage_key, serialized)
        return True

    # ---------------------------------------------------------------------------
    # Memory Snapshots
    # ---------------------------------------------------------------------------

    def create_snapshot(self) -> str:
        """Serialize complete database memory items to a JSON snapshot string."""
        with self._thread_lock:
            connection = self._connect()
            rows = connection.execute("SELECT key, value FROM memory_items").fetchall()
            snapshot_dict = {row["key"]: json.loads(row["value"]) for row in rows}
            return json.dumps(snapshot_dict)

    def restore_snapshot(self, snapshot_data: str) -> None:
        """Restore all memory items from a serialized JSON snapshot string."""
        snapshot_dict = json.loads(snapshot_data)
        with self._thread_lock:
            connection = self._connect()
            connection.execute("DELETE FROM memory_items")
            connection.execute("DELETE FROM memory_versions")
            connection.commit()

        # Write each key back
        for storage_key, val in snapshot_dict.items():
            self._persist_key(storage_key, json.dumps(val, sort_keys=True))

    # ---------------------------------------------------------------------------
    # Memory Locking
    # ---------------------------------------------------------------------------

    async def acquire_lock(self, lock_key: str, owner_id: str, lease_duration_seconds: float = 5.0) -> bool:
        """Acquire a lease-locked resource asynchronously. Returns True if successful."""
        async with self._lock:
            now = asyncio.get_running_loop().time()
            if lock_key in self._locks:
                current_owner, expiration = self._locks[lock_key]
                if now < expiration and current_owner != owner_id:
                    # Lock is held by another process and lease has not expired
                    return False
            
            # Grant/renew lock lease
            self._locks[lock_key] = (owner_id, now + lease_duration_seconds)
            return True

    async def release_lock(self, lock_key: str, owner_id: str) -> bool:
        """Release a locked resource if owned by requesting owner."""
        async with self._lock:
            if lock_key not in self._locks:
                return True
            current_owner, _ = self._locks[lock_key]
            if current_owner == owner_id:
                del self._locks[lock_key]
                return True
            return False

    # ---------------------------------------------------------------------------
    # Vector Memory Store
    # ---------------------------------------------------------------------------

    async def add_vector(self, text: str, metadata: Optional[Dict[str, Any]] = None, doc_id: Optional[str] = None) -> str:
        """Generate and save text string with basic embeddings determinant into Vector Store."""
        vector_id = doc_id or f"vec-{hashlib.md5(os.urandom(16)).hexdigest()[:8]}"
        vector = self._generate_embeddings(text)
        
        with self._thread_lock:
            connection = self._connect()
            connection.execute(
                "INSERT INTO vector_items(id, text, vector, metadata) VALUES(?, ?, ?, ?)"
                "ON CONFLICT(id) DO UPDATE SET text = excluded.text, vector = excluded.vector, metadata = excluded.metadata",
                (vector_id, text, json.dumps(vector), json.dumps(metadata or {})),
            )
            connection.commit()
        
        return vector_id

    async def query_vector(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query top-K similar text entries using local cosine-similarity metrics."""
        query_vector = self._generate_embeddings(query_text)
        results = []

        with self._thread_lock:
            connection = self._connect()
            rows = connection.execute("SELECT id, text, vector, metadata FROM vector_items").fetchall()
            items = [(row["id"], row["text"], json.loads(row["vector"]), json.loads(row["metadata"])) for row in rows]

        for item_id, item_text, item_vector, item_meta in items:
            similarity = self._cosine_similarity(query_vector, item_vector)
            results.append({
                "id": item_id,
                "text": item_text,
                "similarity": similarity,
                "metadata": item_meta,
            })

        # Sort descending by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _generate_embeddings(text: str) -> List[float]:
        """Compute a deterministic 128-dimensional embedding vector based on word hashes."""
        vector = [0.0] * 128
        words = text.lower().split()
        if not words:
            return vector
        
        for word in words:
            # MD5 hash mapped to 128 array bounds
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            index = h % 128
            vector[index] += 1.0
            
        # Cosine normalisation length
        norm = sum(x**2 for x in vector) ** 0.5
        if norm > 0.0:
            vector = [x / norm for x in vector]
            
        return vector

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity score between two float vectors."""
        return sum(x * y for x, y in zip(v1, v2))
