# System Architecture & Design Document (v2 - LLM Agnostic)

## 1. Tech Stack
This package is designed to be lightweight, portable, and **provider-agnostic**, ensuring zero vendor lock-in.

### Core Dependencies
- **Language:** Python 3.9+
- **Web Framework Support:** FastAPI / Starlette (via ASGI middleware). Future support for Flask/Django can be modularized.
- **Asynchronous Processing:** `asyncio` (Native Python) to ensure non-blocking background execution.

### AI & Agentic Layer
- **LLM Engine:** Multi-provider support via the Strategy Pattern. Defaults to `google-genai` (Gemini API), but extensible to any provider (Groq, OpenAI, Ollama).
- **Vector Database / RAG:** `chromadb` (Serverless/Local mode) - Chosen because it doesn't require the end-user to spin up a separate Docker container.

### Notifications & Build
- **HTTP Client:** `httpx` or `aiohttp` for sending non-blocking asynchronous webhook POST requests.
- **Packaging:** `pyproject.toml` with `hatchling`.

---

## 2. Application Flow & Architecture

The system operates on an "Intercept, Release, and Investigate" model.

### Step 1: Interception (The Middleware)
- The user wraps their FastAPI app with `AgenticSREMiddleware`.
- When an unhandled exception occurs, the middleware intercepts it.

### Step 2: Release (Non-Blocking Handoff)
- The middleware immediately returns a standard JSON `500 Internal Server Error` response to the end user. 
- Simultaneously, it spawns an `asyncio.create_task(investigate_bug())` background process.

### Step 3: Context Extraction & Sanitization
- The background task extracts the full traceback and request data.
- The `Sanitizer` module scrubs the payload using Regex to remove sensitive data (PII).

### Step 4: The Agentic Pipeline (Provider-Agnostic RAG + AI)
- **RAG Retrieval:** Queries local `chromadb` for similar past errors or documentation.
- **LLM Synthesis via Strategy Pattern:** The system hands the sanitized data to an `AIProviderInterface`. Depending on user configuration, this interface routes the request to the Gemini API (or Groq/Ollama in the future).
- The active AI provider returns a structured JSON response containing: `root_cause_hypothesis`, `affected_component`, and `suggested_fix`.

### Step 5: Dispatch
- The `Dispatcher` formats the JSON response into a Markdown payload and sends it via webhook to Slack or Discord.

---

## 3. Folder and File Structure (Updated for Provider Pattern)

```text
agentic-sre/
│
├── pyproject.toml              # Build system, metadata, dependencies (PyPI config)
├── .env.example                # Template for required environment variables
├── README.md                   
├── LICENSE                     
│
├── src/
│   └── agentic_sre/            
│       ├── __init__.py         
│       ├── middleware.py       
│       │
│       ├── core/               
│       │   ├── __init__.py
│       │   ├── extractor.py    
│       │   └── sanitizer.py    
│       │
│       ├── ai/                 # Brains of the operation (LLM Agnostic)
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract Base Class (BaseAIProvider)
│       │   ├── gemini.py       # Implementation for Google Gemini
│       │   ├── groq.py         # (Future) Implementation for Groq/Llama
│       │   └── vector_store.py # Manages ChromaDB RAG interactions
│       │
│       └── notifications/      
│           ├── __init__.py
│           ├── dispatcher.py   
│           └── webhooks.py     
│
├── tests/                      
│   ├── test_middleware.py
│   ├── test_sanitizer.py
│   └── test_ai_formatting.py
│
└── examples/                   
    └── fastapi_demo/
        └── main.py             
```