"""Agentic SRE Middleware for FastAPI / Starlette applications.

Intercepts unhandled 500 exceptions, returns immediate JSON responses to clients,
and triggers non-blocking background AI investigation tasks.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Coroutine, Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from agentic_sre.ai.gemini import GeminiProvider
from agentic_sre.ai.vector_store import MemoryStore
from agentic_sre.core.deduplicator import CrashDeduplicator
from agentic_sre.core.extractor import Extractor
from agentic_sre.notifications.webhooks import close_shared_http_client, dispatch_alerts

logger = logging.getLogger("agentic_sre")

# Shared module-level instances for client and connection reuse
_DEFAULT_MEMORY_STORE = MemoryStore()
_DEFAULT_AI_PROVIDER = GeminiProvider()
_DEFAULT_DEDUPLICATOR = CrashDeduplicator()

# Maximum concurrent background investigation tasks allowed to prevent OOM
DEFAULT_MAX_BACKGROUND_TASKS = 100


async def _default_investigate_task(
    exc: Exception,
    request: Request,
    pre_extracted_context: Optional[dict[str, Any]] = None,
) -> None:
    """Background task executing non-blocking AI root-cause analysis and alert dispatch.

    Runs asynchronously via `asyncio.create_task` after the HTTP response has
    been returned to the client.

    Args:
        exc: The intercepted exception instance.
        request: The Starlette/FastAPI Request object.
        pre_extracted_context: Optional pre-extracted crash context dictionary.

    Fail-Silent Rule:
        This function MUST catch all internal exceptions and log them locally to
        stderr. It must NEVER throw or bubble up exceptions to the host process.
    """
    try:
        if pre_extracted_context:
            crash_context = pre_extracted_context
        else:
            extractor = Extractor()
            crash_context = extractor.extract(exc, request)

        logger.info(
            f"[Agentic-SRE] Background investigation started for crash on "
            f"{crash_context['method']} {crash_context['url']} "
            f"[Correlation ID: {crash_context.get('correlation_id', 'none')}]"
        )

        stack_trace_str = crash_context.get("stack_trace", "")

        # RAG Search: Retrieve similar historical crashes from ChromaDB
        memory_store = _DEFAULT_MEMORY_STORE
        historical_crashes = await memory_store.search_similar_crashes(
            stack_trace_str, limit=3
        )
        crash_context["historical_context"] = historical_crashes

        # AI Root Cause Analysis via Strategy Pattern (informed by RAG memory)
        ai_provider = _DEFAULT_AI_PROVIDER
        ai_rca = await ai_provider.analyze_error(crash_context)

        # RAG Persistence: Save new crash context & AI fix to ChromaDB vector store
        await memory_store.store_crash(stack_trace_str, ai_rca)

        # Dispatch alerts asynchronously to Slack and Discord webhooks
        await dispatch_alerts(crash_context, ai_rca)

    except Exception as background_exc:
        # Guarantee Fail-Silent rule: catch and log without raising
        logger.error(
            f"[Agentic-SRE] Fail-silent exception in background task: {background_exc}",
            exc_info=True,
        )


class AgenticSREMiddleware(BaseHTTPMiddleware):
    """ASGI Middleware that intercepts unhandled server exceptions (500 errors).

    Returns an immediate standard JSON response to the user to maintain zero latency
    impact, while delegating bug investigation to a non-blocking background task.

    Attributes:
        app: The ASGI application instance.
        enabled: Optional boolean flag to enable or disable middleware interception.
        investigate_coro: Callable coroutine function for background investigation.
        max_background_tasks: Upper limit on active background tasks to prevent OOM memory kills.
        deduplicator: Optional CrashDeduplicator instance for alert throttling.
    """

    __slots__ = (
        "enabled",
        "investigate_coro",
        "_background_tasks",
        "max_background_tasks",
        "deduplicator",
    )

    def __init__(
        self,
        app: ASGIApp,
        enabled: bool = True,
        investigate_coro: Optional[
            Callable[[Exception, Request], Coroutine[Any, Any, None]]
        ] = None,
        max_background_tasks: int = DEFAULT_MAX_BACKGROUND_TASKS,
        deduplicator: Optional[CrashDeduplicator] = _DEFAULT_DEDUPLICATOR,
    ) -> None:
        """Initializes the AgenticSREMiddleware.

        Args:
            app: The Starlette/FastAPI application instance.
            enabled: Whether the middleware is actively intercepting exceptions. Defaults to True.
            investigate_coro: Optional custom background task coroutine function.
            max_background_tasks: Maximum pending background tasks permitted. Defaults to 100.
            deduplicator: Optional CrashDeduplicator instance. Defaults to shared singleton.
        """
        super().__init__(app)
        self.enabled = enabled
        self.investigate_coro = investigate_coro or _default_investigate_task
        self.max_background_tasks = max_background_tasks
        self.deduplicator = deduplicator
        self._background_tasks: Set[asyncio.Task[Any]] = set()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Dispatches the HTTP request, catching any unhandled exceptions.

        Args:
            request: The incoming Starlette/FastAPI request object.
            call_next: Callable to process the request through downstream middleware/routes.

        Returns:
            Response: Starlette Response object (either the route's response or an instant 500 JSON response).
        """
        if not self.enabled:
            return await call_next(request)

        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(
                f"[Agentic-SRE] Intercepted 500 crash on {request.method} {request.url.path}: "
                f"{type(exc).__name__}: {exc}"
            )

            # 1. Memory Safety: Backpressure check to prevent OOM worker crashes
            if len(self._background_tasks) >= self.max_background_tasks:
                logger.warning(
                    f"[Agentic-SRE] Backpressure threshold reached ({len(self._background_tasks)}/{self.max_background_tasks} active tasks). "
                    f"Throttling background AI task to protect server memory."
                )
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "Internal Server Error",
                        "error": "An unhandled exception occurred. Background investigation throttled due to high server load.",
                    },
                )

            # 2. Extract crash context and check deduplication
            extractor = Extractor()
            crash_context = extractor.extract(exc, request)

            if self.deduplicator and self.deduplicator.should_suppress(crash_context):
                logger.info(
                    f"[Agentic-SRE] Suppressing duplicate crash alert for {crash_context.get('exception_type')} "
                    f"at {crash_context.get('file_name')}:{crash_context.get('line_number')} (Deduplication TTL active)."
                )
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "Internal Server Error",
                        "error": "An unhandled exception occurred. Agentic-SRE investigation suppressed (duplicate incident).",
                    },
                )

            # 3. Fire and Forget: Spawn background task with strong reference set
            task = asyncio.create_task(self.investigate_coro(exc, request))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

            # Return immediate standard JSON 500 response to client
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal Server Error",
                    "error": "An unhandled exception occurred. Agentic-SRE background investigation triggered.",
                },
            )

    async def flush_pending_tasks(self, timeout: float = 5.0) -> None:
        """Flushes and awaits all pending background investigation tasks during ASGI graceful shutdown.

        Args:
            timeout: Maximum time in seconds to wait for pending tasks before cancelling. Defaults to 5.0.
        """
        if not self._background_tasks:
            await close_shared_http_client()
            return

        logger.info(
            f"[Agentic-SRE] Flushing {len(self._background_tasks)} pending background AI task(s) "
            f"during server shutdown (timeout={timeout}s)..."
        )
        tasks = list(self._background_tasks)
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                "[Agentic-SRE] Shutdown timeout reached. Cancelling remaining pending tasks..."
            )
            for task in tasks:
                if not task.done():
                    task.cancel()
        finally:
            self._background_tasks.clear()
            await close_shared_http_client()
