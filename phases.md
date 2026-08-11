# Project Roadmap & Implementation Phases

This document breaks down the development of `agentic-sre` into structured, actionable sprints across a 4-week timeline.

---

## Phase 1: Core Middleware & Security Plumbing (Week 1)
**Goal:** Intercept crashes, extract clean stack traces, scrub sensitive data, and hand off execution non-blockingly without delaying the host app's response.

### Milestones & Deliverables
1. **Package Blueprint Setup**
   - Configure `pyproject.toml` with build tools (`hatchling`), dependencies (`fastapi`, `httpx`, `google-genai`, `chromadb`), and package metadata.
   - Set up the standard `src/agentic_sre` directory layout.

2. **ASGI Middleware Implementation (`middleware.py`)**
   - Write `AgenticSREMiddleware` subclassing Starlette's `BaseHTTPMiddleware` or custom ASGI callable.
   - Implement exception catching for standard `500` errors.
   - Instantly return the standard error response to the user while spawning a background thread using `asyncio.create_task()` for non-blocking analysis.

3. **Context Extractor (`extractor.py`)**
   - Capture full stack trace string using Python's `traceback` module.
   - Extract failing filename, exact line number, function name, and code snippet.
   - Capture request URL, HTTP method, and sanitized request headers.

4. **Data Sanitizer (`sanitizer.py`)**
   - Implement regex-based PII scrubbing.
   - Automatically redact authorization tokens, passwords, API keys, bearer tokens, credit cards, and sensitive env variables.

5. **Local Middleware Testing**
   - Create `examples/fastapi_demo/main.py` containing deliberate crashing routes (e.g., `ZeroDivisionError`, `KeyError`).
   - Verify that crashing endpoints respond instantly while the background task receives the scrubbed stack trace.

---

## Phase 2: AI Engine & Webhook Dispatcher (Week 2)
**Goal:** Connect the Gemini API to analyze errors, generate structured root cause analysis (RCA), and deliver formatted alerts to Slack/Discord.

### Milestones & Deliverables
1. **Gemini Integration (`ai/gemini.py`)**
   - Integrate `google-genai` SDK.
   - Implement strict system prompt forcing the model into a "Senior SRE Detective" persona.
   - Enforce structured JSON output containing:
     - `error_summary`
     - `root_cause_hypothesis`
     - `failing_component`
     - `suggested_fix`

2. **Resilience & Fail-Silent Protocols**
   - Wrap all AI calls in `try/except` blocks to satisfy the **Fail-Silent Rule** (preventing AI errors from breaking the host app).
   - Set strict HTTP timeouts (`timeout=5.0s`) for external Gemini API calls.

3. **Webhook Dispatcher (`notifications/`)**
   - Build `dispatcher.py` to convert Gemini's JSON output into rich Markdown payloads (using Slack Block Kit or Discord Embeds).
   - Build `webhooks.py` using `httpx.AsyncClient` to asynchronously POST messages to Slack/Discord webhooks without blocking.

4. **Phase 2 Integration Verification**
   - Trigger a crash in the demo app and verify that a Slack message arrives within 3–5 seconds containing a accurate fix suggestion.

---

## Phase 3: RAG & Agentic Memory (Week 3)
**Goal:** Equip the AI agent with local document retrieval (ChromaDB) so it can cross-reference project documentation and past crashes.

### Milestones & Deliverables
1. **Local Vector Store Setup (`ai/vector_store.py`)**
   - Initialize `chromadb` in local persistent or in-memory mode.
   - Write an ingestion helper to read local Markdown files (`README.md`, API docs, architecture specs) and store embeddings.

2. **RAG Pipeline Integration**
   - When a crash occurs, perform vector search against `chromadb` using the stack trace as a query.
   - Retrieve top matching documentation chunks or past error fixes.
   - Inject the retrieved context into the Gemini prompt: *"Here is relevant documentation from the repository: ..."*

3. **Historical Error Deduplication**
   - Store past scrubbed stack trace hashes in ChromaDB.
   - If an error has been seen previously, inform the team: *"This error occurred 3 times this week. Previous fix suggested was..."*

---

## Phase 4: Packaging, Testing & PyPI Publishing (Week 4)
**Goal:** Polish, write unit tests, generate documentation, publish to PyPI, and prepare resume presentation.

### Milestones & Deliverables
1. **Automated Testing Suite (`tests/`)**
   - Write unit tests for regex sanitization (`test_sanitizer.py`).
   - Write async integration tests for middleware exception catching using `httpx.AsyncClient` (`test_middleware.py`).

2. **PyPI Publishing**
   - Build source distributions and wheels: `python -m build`.
   - Publish package to PyPI: `twine upload dist/*`.
   - Verify installation via `pip install agentic-sre`.

3. **Documentation & Presentation**
   - Write a compelling `README.md` complete with usage examples, architectural diagram, and installation commands.
   - Prepare bullet points highlighting this project for SRE, Backend, and AI Engineering roles.
