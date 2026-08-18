import asyncio
import os
import shutil
import sys
sys.path.insert(0, "src")

from agentic_sre.ai.vector_store import MemoryStore

TEST_DB_PATH = ".chroma_test_db"


async def test_memory_store():
    # Cleanup previous test db if exists
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)

    store = MemoryStore(db_path=TEST_DB_PATH)

    stack_trace_1 = (
        "Traceback (most recent call last):\n"
        "  File 'checkout.py', line 84, in checkout_endpoint\n"
        "    discount = payload['discount_code']\n"
        "KeyError: 'discount_code'"
    )

    ai_rca_1 = {
        "error_summary": "Missing discount_code key in payload.",
        "root_cause_hypothesis": "The payload dictionary accessed discount_code without get().",
        "failing_component": "app/routers/checkout.py:84 in checkout_endpoint()",
        "suggested_fix": "discount = payload.get('discount_code', None)"
    }

    print("--- Test 1: Store Crash in MemoryStore ---")
    await store.store_crash(stack_trace_1, ai_rca_1)
    print("PASS: Successfully stored crash into ChromaDB.")

    print("\n--- Test 2: Search Similar Crash ---")
    query_trace = (
        "Traceback (most recent call last):\n"
        "  File 'cart.py', line 42, in process_cart\n"
        "    code = data['discount_code']\n"
        "KeyError: 'discount_code'"
    )

    results = await store.search_similar_crashes(query_trace, limit=2)
    print(f"Retrieved {len(results)} matching crash(es) from ChromaDB:")
    for res in results:
        print(" -> Summary:", res.get("error_summary"))
        print(" -> Suggested Fix:", res.get("suggested_fix"))

    assert len(results) > 0
    assert "discount_code" in results[0]["error_summary"]
    print("PASS: ChromaDB similarity search returned matching historical fix.")

    # Clean up test DB
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)
    print("\nALL VECTOR STORE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(test_memory_store())
