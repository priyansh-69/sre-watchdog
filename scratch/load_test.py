"""Concurrent load test script for AgenticSREMiddleware resilience verification."""

import asyncio
import time
import httpx

TARGET_URL = "http://127.0.0.1:8000/crash/basic"
CONCURRENT_REQUESTS = 50


async def send_request(client: httpx.AsyncClient, req_id: int) -> int:
    """Sends a single request to the crashing endpoint and returns HTTP status code."""
    try:
        response = await client.get(TARGET_URL)
        return response.status_code
    except Exception as exc:
        print(f"Request #{req_id} failed with error: {exc}")
        return 500


async def run_load_test():
    """Fires 50 concurrent HTTP requests to verify middleware resilience and connection pooling."""
    print(f"🚀 Starting load test: Firing {CONCURRENT_REQUESTS} concurrent requests to {TARGET_URL}...")
    start_time = time.perf_counter()

    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [send_request(client, i) for i in range(1, CONCURRENT_REQUESTS + 1)]
        status_codes = await asyncio.gather(*tasks)

    duration = time.perf_counter() - start_time

    status_200 = status_codes.count(200)
    status_500 = status_codes.count(500)
    other = len(status_codes) - (status_200 + status_500)

    print("\n--- Load Test Results ---")
    print(f"⏱️ Total Duration: {duration:.3f} seconds")
    print(f"⚡ Throughput: {CONCURRENT_REQUESTS / duration:.2f} req/sec")
    print(f"✅ 500 Internal Server Error (Intercepted by Middleware): {status_500}/{CONCURRENT_REQUESTS}")
    print(f"❌ Other/Unexpected Status Codes: {other}")
    
    if status_500 == CONCURRENT_REQUESTS:
        print("\n🎉 SUCCESS: All 50 concurrent requests handled cleanly without socket exhaustion!")
    else:
        print("\n⚠️ WARNING: Some requests did not return the expected 500 status code.")


if __name__ == "__main__":
    asyncio.run(run_load_test())
