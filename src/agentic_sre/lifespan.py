"""Lifespan context manager for Agentic-SRE task flushing on server shutdown."""

from contextlib import asynccontextmanager
import logging
from typing import Any, AsyncGenerator

from agentic_sre.notifications.webhooks import close_shared_http_client

logger = logging.getLogger("agentic_sre")


@asynccontextmanager
async def sre_lifespan(app: Any) -> AsyncGenerator[None, None]:
    """ASGI Lifespan context manager that gracefully flushes connections on shutdown.

    Usage in FastAPI:
        app = FastAPI(lifespan=sre_lifespan)
        app.add_middleware(AgenticSREMiddleware)
    """
    yield
    logger.info("[Agentic-SRE] Lifespan shutdown: Closing shared HTTP client connections...")
    await close_shared_http_client()
