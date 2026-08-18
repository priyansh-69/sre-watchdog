import os
import sys
sys.path.insert(0, "src")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
import uvicorn
from agentic_sre import AgenticSREMiddleware

app = FastAPI(title="Agentic-SRE Demo API")

# Attach Agentic-SRE Middleware
app.add_middleware(AgenticSREMiddleware)


@app.get("/")
async def root():
    """Healthy root endpoint."""
    return {"status": "ok", "message": "Agentic-SRE Demo API is running safely!"}


@app.get("/crash")
@app.get("/crash/basic")
async def crash_basic():
    """Crashing endpoint triggering ZeroDivisionError."""
    result = 100 / 0  # Deliberate division by zero crash
    return {"result": result}


def _infinite_recursion(depth: int = 0) -> None:
    """Helper function to generate a massive stack trace via recursion."""
    _infinite_recursion(depth + 1)


@app.get("/crash/recursion")
async def crash_recursion():
    """Crashing endpoint triggering RecursionError for testing stack trace truncation."""
    _infinite_recursion()
    return {"status": "should not reach here"}


if __name__ == "__main__":
    print("Starting Agentic-SRE Demo Server on http://127.0.0.1:8000 ...")
    uvicorn.run("demo:app", host="127.0.0.1", port=8000, reload=True)
