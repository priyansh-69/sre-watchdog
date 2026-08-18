"""Async unit tests for MemoryStore vector storage and retrieval."""

import os
import shutil

import pytest

from agentic_sre.ai.vector_store import MemoryStore

TEST_DB_PATH = ".chroma_pytest_db"


@pytest.fixture(autouse=True)
def cleanup_db():
    """Fixture to ensure temporary ChromaDB directory is cleaned up before and after tests."""
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH, ignore_errors=True)
    yield
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH, ignore_errors=True)


@pytest.mark.asyncio
async def test_store_and_search_crash():
    store = MemoryStore(db_path=TEST_DB_PATH)

    stack_trace = (
        "Traceback (most recent call last):\n"
        "  File 'checkout.py', line 84, in checkout\n"
        "    discount = payload['discount_code']\n"
        "KeyError: 'discount_code'"
    )
    ai_rca = {
        "error_summary": "Missing discount_code key in payload.",
        "root_cause_hypothesis": "The payload dictionary accessed discount_code without get().",
        "failing_component": "app/routers/checkout.py:84 in checkout()",
        "suggested_fix": "discount = payload.get('discount_code', None)",
    }

    # Store crash
    await store.store_crash(stack_trace, ai_rca)

    # Search crash
    results = await store.search_similar_crashes(stack_trace, limit=1)
    assert len(results) == 1
    assert results[0]["error_summary"] == "Missing discount_code key in payload."
    assert "discount_code" in results[0]["suggested_fix"]


@pytest.mark.asyncio
async def test_fail_silent_on_invalid_db():
    # Pass an invalid db path or handle uninitialized store gracefully
    store = MemoryStore(db_path="/dev/null/invalid_path")
    results = await store.search_similar_crashes("Some stack trace", limit=1)
    assert results == []
