"""In-memory sliding-window crash deduplicator for Agentic-SRE.

Prevents alert fatigue and LLM API cost explosion during outage spikes.
"""

from collections import OrderedDict
import hashlib
import time
from typing import Any, Dict, Optional


class CrashDeduplicator:
    """Sliding-window deduplicator that suppresses duplicate crash alerts within a TTL window.

    Attributes:
        ttl_seconds: Duration in seconds to suppress duplicate crashes. Defaults to 900 (15 minutes).
        max_cache_size: Maximum entries in the deduplication cache before eviction. Defaults to 1000.
    """

    def __init__(self, ttl_seconds: int = 900, max_cache_size: int = 1000) -> None:
        """Initializes CrashDeduplicator.

        Args:
            ttl_seconds: Suppress duplicates seen within this timeframe. Defaults to 900 (15m).
            max_cache_size: Upper limit on cached fingerprints to bound memory. Defaults to 1000.
        """
        self.ttl_seconds = ttl_seconds
        self.max_cache_size = max_cache_size
        self._cache: OrderedDict[str, float] = OrderedDict()

    def _generate_fingerprint(self, crash_context: Dict[str, Any]) -> str:
        """Generates a deterministic SHA-256 fingerprint for a crash context.

        Fingerprint combines exception type, file name, line number, function name,
        and exception message prefix.

        Args:
            crash_context: Dictionary containing extracted crash metadata.

        Returns:
            SHA-256 hex string identifying the unique crash signature.
        """
        exc_type = str(crash_context.get("exception_type", "Exception"))
        file_name = str(crash_context.get("file_name", "unknown"))
        line_num = str(crash_context.get("line_number", 0))
        func_name = str(crash_context.get("function_name", "unknown"))
        msg = str(crash_context.get("exception_message", ""))[:100]

        raw_key = f"{exc_type}:{file_name}:{line_num}:{func_name}:{msg}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def should_suppress(self, crash_context: Dict[str, Any]) -> bool:
        """Determines if a crash is a duplicate within the configured TTL window.

        Args:
            crash_context: Dictionary containing extracted crash metadata.

        Returns:
            True if crash should be suppressed, False if it is a new unique crash.
        """
        now = time.time()
        self._cleanup_expired(now)

        fingerprint = self._generate_fingerprint(crash_context)
        last_seen = self._cache.get(fingerprint)

        if last_seen is not None and (now - last_seen) < self.ttl_seconds:
            self._cache.move_to_end(fingerprint)
            return True

        # Evict oldest entry in O(1) time if cache exceeds bounds
        if len(self._cache) >= self.max_cache_size:
            self._cache.popitem(last=False)

        self._cache[fingerprint] = now
        return False

    def _cleanup_expired(self, current_time: float) -> None:
        """Removes entries older than ttl_seconds to prevent memory growth."""
        expired_keys = [
            key for key, timestamp in self._cache.items()
            if (current_time - timestamp) >= self.ttl_seconds
        ]
        for key in expired_keys:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Clears all cached deduplication entries."""
        self._cache.clear()
