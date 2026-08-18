"""ChromaDB local vector store for Agentic-SRE historical crash memory."""

import asyncio
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agentic_sre")

DEFAULT_DB_PATH = ".chroma_db"
COLLECTION_NAME = "crash_history"


DEFAULT_MAX_RECORDS = 5000


class MemoryStore:
    """Local vector store for crash memory using ChromaDB."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        max_workers: int = 3,
        max_records: int = DEFAULT_MAX_RECORDS,
    ) -> None:
        """Initializes MemoryStore with persistent storage, a Bulkhead executor, and record eviction bounds.

        Args:
            db_path: Folder path where ChromaDB stores vectors locally. Defaults to '.chroma_db'.
            max_workers: Maximum worker threads for ChromaDB I/O isolation bulkhead. Defaults to 3.
            max_records: Maximum records allowed in vector store before FIFO eviction. Defaults to 5000.
        """
        self.db_path = db_path
        self.max_records = max_records
        self._client: Optional[Any] = None
        self._collection: Optional[Any] = None
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="agentic_sre_chroma",
        )

    async def _run_in_bulkhead(self, func: Any, *args: Any) -> Any:
        """Executes a blocking function inside the private Bulkhead ThreadPoolExecutor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, func, *args)

    def _generate_embedding(self, text: str, dim: int = 384) -> List[float]:
        """Generates a lightweight, deterministic 384-dimensional embedding vector.

        Avoids network downloads of ONNX models while ensuring deterministic vector similarity.

        Args:
            text: Input string to embed.
            dim: Dimension of vector output. Defaults to 384.

        Returns:
            List[float]: Normalized vector representation of text.
        """
        if not text:
            return [0.0] * dim

        vec = [0.0] * dim
        for i, char in enumerate(text):
            idx = (ord(char) + i * 31) % dim
            vec[idx] += 1.0

        magnitude = sum(x * x for x in vec) ** 0.5
        if magnitude > 0:
            vec = [x / magnitude for x in vec]

        return vec

    def _get_collection(self) -> Any:
        """Lazily initializes ChromaDB client and collection with Fail-Silent error handling."""
        if self._collection is not None:
            return self._collection

        try:
            import chromadb

            abs_path = os.path.abspath(self.db_path)
            self._client = chromadb.PersistentClient(path=abs_path)
            # Pass embedding_function=None to prevent ChromaDB from downloading ONNX models
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=None,
            )
            return self._collection
        except Exception as exc:
            logger.error(
                f"[Agentic-SRE] Fail-silent error initializing ChromaDB: {exc}",
                exc_info=True,
            )
            return None

    async def search_similar_crashes(
        self, stack_trace_str: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Searches ChromaDB for historically similar stack traces.

        Args:
            stack_trace_str: The current crash stack trace query.
            limit: Maximum number of similar results to return. Defaults to 3.

        Returns:
            List of dictionaries containing matched past crash details and suggested fixes.

        Fail-Silent Guarantee:
            If ChromaDB fails or is corrupted, returns an empty list `[]` without raising.
        """
        try:
            collection = await self._run_in_bulkhead(self._get_collection)
            if collection is None or not stack_trace_str:
                return []

            query_vec = self._generate_embedding(stack_trace_str)

            results = await self._run_in_bulkhead(
                lambda: collection.query(
                    query_embeddings=[query_vec],
                    n_results=limit,
                )
            )

            similar_crashes: List[Dict[str, Any]] = []
            if results and results.get("metadatas") and len(results["metadatas"]) > 0:
                metadatas_list = results["metadatas"][0]
                distances_list = (
                    results.get("distances", [[]])[0]
                    if results.get("distances")
                    else []
                )
                documents_list = (
                    results.get("documents", [[]])[0]
                    if results.get("documents")
                    else []
                )

                for idx, meta in enumerate(metadatas_list):
                    item = dict(meta) if meta else {}
                    if idx < len(documents_list):
                        item["stack_trace"] = documents_list[idx]
                    if idx < len(distances_list):
                        item["distance"] = distances_list[idx]
                    similar_crashes.append(item)

            return similar_crashes

        except Exception as exc:
            logger.error(
                f"[Agentic-SRE] Fail-silent error searching ChromaDB: {exc}",
                exc_info=True,
            )
            return []

    async def store_crash(self, stack_trace_str: str, ai_rca: Dict[str, Any]) -> None:
        """Stores a crash stack trace document and AI RCA metadata in ChromaDB.

        Args:
            stack_trace_str: The sanitized crash stack trace string.
            ai_rca: Dictionary containing AI root cause analysis.

        Fail-Silent Guarantee:
            Catches all DB errors (including multi-worker SQLite lock contention),
            logs to stderr, and completes without raising.
        """
        if not stack_trace_str:
            return

        record_id = uuid.uuid4().hex
        metadata = {
            "error_summary": str(ai_rca.get("error_summary", "")),
            "root_cause_hypothesis": str(ai_rca.get("root_cause_hypothesis", "")),
            "failing_component": str(ai_rca.get("failing_component", "")),
            "suggested_fix": str(ai_rca.get("suggested_fix", "")),
        }
        embedding_vec = self._generate_embedding(stack_trace_str)

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                collection = await self._run_in_bulkhead(self._get_collection)
                if collection is None:
                    return

                # Evict oldest entry if collection exceeds max_records to prevent disk exhaustion
                try:
                    count = await self._run_in_bulkhead(collection.count)
                    if count >= self.max_records:
                        oldest = await self._run_in_bulkhead(
                            lambda: collection.get(limit=1)
                        )
                        if oldest and oldest.get("ids"):
                            await self._run_in_bulkhead(
                                lambda: collection.delete(ids=[oldest["ids"][0]])
                            )
                except Exception as evict_err:
                    logger.warning(
                        f"[Agentic-SRE] Vector store eviction check failed: {evict_err}"
                    )

                await self._run_in_bulkhead(
                    lambda: collection.add(
                        documents=[stack_trace_str],
                        embeddings=[embedding_vec],
                        metadatas=[metadata],
                        ids=[record_id],
                    )
                )
                logger.info(
                    f"[Agentic-SRE] Stored crash record {record_id} into ChromaDB vector store."
                )
                break
            except Exception as exc:
                if "locked" in str(exc).lower() and attempt < max_retries:
                    await asyncio.sleep(0.1 * (attempt + 1))
                    continue
                logger.error(
                    f"[Agentic-SRE] Fail-silent error storing crash in ChromaDB: {exc}",
                    exc_info=True,
                )
                break

    def close(self) -> None:
        """Gracefully shuts down the dedicated ThreadPoolExecutor bulkhead."""
        self._executor.shutdown(wait=False, cancel_futures=True)
