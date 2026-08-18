import asyncio
import os
import shutil
import sys
sys.path.insert(0, "src")

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient
from agentic_sre import AgenticSREMiddleware
from agentic_sre.ai.vector_store import MemoryStore

TEST_DB_PATH = ".chroma_rag_pipeline_test"


async def verify_rag_pipeline():
    # 1. Clean up old test vector DB if exists
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)

    # 2. Seed memory store with a known past crash fix
    store = MemoryStore(db_path=TEST_DB_PATH)
    known_stack_trace = (
        "Traceback (most recent call last):\n"
        "  File 'checkout.py', line 84, in checkout_endpoint\n"
        "    discount = payload['discount_code']\n"
        "KeyError: 'discount_code'"
    )
    known_fix = {
        "error_summary": "Missing discount_code key in payload.",
        "root_cause_hypothesis": "The payload dictionary accessed discount_code without get().",
        "failing_component": "app/routers/checkout.py:84 in checkout_endpoint()",
        "suggested_fix": "discount = payload.get('discount_code', None)"
    }

    print("--- 1. Seeding Vector Store with Past Fix ---")
    await store.store_crash(known_stack_trace, known_fix)
    print("Seeded 1 past crash solution into ChromaDB.")

    print("\n--- 2. Querying RAG Memory for Similar Crash ---")
    new_query_trace = (
        "Traceback (most recent call last):\n"
        "  File 'order.py', line 42, in process_order\n"
        "    code = payload['discount_code']\n"
        "KeyError: 'discount_code'"
    )
    matches = await store.search_similar_crashes(new_query_trace, limit=2)
    print(f"Retrieved {len(matches)} historical match(es):")
    for m in matches:
        print("  -> Summary:", m.get("error_summary"))
        print("  -> Fix:", m.get("suggested_fix"))

    assert len(matches) > 0
    assert "discount_code" in matches[0]["error_summary"]
    print("PASS: RAG Memory successfully retrieved past solution!")

    # 3. Clean up test DB
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)
    print("\nALL RAG PIPELINE TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(verify_rag_pipeline())
