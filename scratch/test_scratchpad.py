import asyncio
import sys
sys.path.insert(0, "src")

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient
from agentic_sre import AgenticSREMiddleware

async def crashing_endpoint(request):
    raise ValueError("Simulated database connection failure")

async def healthy_endpoint(request):
    return PlainTextResponse("OK")

app = Starlette(routes=[
    Route("/crash", crashing_endpoint),
    Route("/ok", healthy_endpoint),
])

app.add_middleware(AgenticSREMiddleware)

def main():
    client = TestClient(app, raise_server_exceptions=False)
    
    print("--- Test 1: Healthy Route ---")
    res1 = client.get("/ok")
    print("Status:", res1.status_code, "Body:", res1.text)
    assert res1.status_code == 200
    
    print("\n--- Test 2: Crashing Route (Intercepted 500) ---")
    res2 = client.get("/crash")
    print("Status:", res2.status_code)
    print("JSON Response:", res2.json())
    assert res2.status_code == 500
    assert res2.json()["detail"] == "Internal Server Error"
    
    print("\nSUCCESS: AgenticSREMiddleware intercepted exception and returned instant 500 response.")

if __name__ == "__main__":
    main()
