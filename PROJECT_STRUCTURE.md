# Project Directory Structure

Overview of the `agentic-sre` repository structure, folder layout, and component descriptions.

## 📁 Repository Tree

```text
priyansh-69/sre-watchdog
├── .env                              # Environment variables (API keys, webhooks)
├── .env.example                      # Template environment variable configuration
├── .gitignore                        # Git exclusion rules
├── Architecture.md                   # System design & component architecture document
├── PRD.md                            # Product Requirements Document
├── PROJECT_STRUCTURE.md              # Project structure and directory map
├── README.md                         # Project introduction, setup, and usage guide
├── demo.py                           # Standalone end-to-end interactive demo
├── design.md                         # Detailed technical design specifications
├── memory.md                         # Project progress & persistent state log
├── phases.md                         # Implementation roadmap & phase breakdown
├── pyproject.toml                    # Python project configuration & dependencies
├── rules.md                          # Coding guidelines and SRE guardrails
│
├── scratch/                          # Local experimental & developer scratchpad scripts
│   ├── test_ai_provider_scratch.py   # AI provider module test scratchpad
│   ├── test_data_handling_scratch.py # Data extraction & sanitization test scratchpad
│   ├── test_notifications_scratch.py # Webhook notification test scratchpad
│   ├── test_rag_pipeline_scratch.py  # Historical crash RAG pipeline test scratchpad
│   ├── test_scratchpad.py            # Initial middleware behavior scratchpad
│   └── test_vector_store_scratch.py  # ChromaDB vector store test scratchpad
│
├── src/                              # Main application source code
│   └── agentic_sre/                  # Core package directory
│       ├── __init__.py               # Package exports (AgenticSREMiddleware)
│       ├── middleware.py             # FastAPI / Starlette 500 interception middleware
│       │
│       ├── ai/                       # AI Root Cause Analysis & RAG modules
│       │   ├── __init__.py           # AI package initializer
│       │   ├── base.py               # Abstract Base Class for AI providers
│       │   ├── gemini.py             # Google Gemini AI provider implementation
│       │   └── vector_store.py       # ChromaDB vector store for RCA historical indexing
│       │
│       ├── core/                     # Core diagnostic & security utilities
│       │   ├── __init__.py           # Core package initializer
│       │   ├── extractor.py          # Stack trace & request context extractor
│       │   └── sanitizer.py          # PII & secrets redaction sanitizer
│       │
│       └── notifications/            # Alerting & notification dispatcher
│           ├── __init__.py           # Notifications package initializer
│           ├── dispatcher.py         # Async notification manager & queue
│           └── webhooks.py           # Discord & Slack webhook formatters & senders
│
└── tests/                            # Automated test suite
    ├── __init__.py                   # Test package initializer
    ├── test_middleware.py            # Middleware exception handling tests
    ├── test_sanitizer.py             # PII redaction unit tests
    └── test_vector_store.py          # RAG vector store indexing & query tests
```

---

## 🛠️ Directory & File Descriptions

### Root Files
| File | Description |
| :--- | :--- |
| [`.env`](file:///Users/priyanshsmac/Developer/Projects/python/.env) | Stores local secret configurations like `GEMINI_API_KEY`, `DISCORD_WEBHOOK_URL`, etc. |
| [`.env.example`](file:///Users/priyanshsmac/Developer/Projects/python/.env.example) | Template file outlining required environment variables for deployment. |
| [`.gitignore`](file:///Users/priyanshsmac/Developer/Projects/python/.gitignore) | Git ignore patterns for virtual environments, `.env`, caches, and scratch files. |
| [`Architecture.md`](file:///Users/priyanshsmac/Developer/Projects/python/Architecture.md) | High-level system architecture, data flow diagrams, and component interactions. |
| [`PRD.md`](file:///Users/priyanshsmac/Developer/Projects/python/PRD.md) | Product Requirements Document outlining goals, user stories, and features. |
| [`PROJECT_STRUCTURE.md`](file:///Users/priyanshsmac/Developer/Projects/python/PROJECT_STRUCTURE.md) | Comprehensive map of project files and directories (this file). |
| [`README.md`](file:///Users/priyanshsmac/Developer/Projects/python/README.md) | Quickstart guide, installation steps, and usage examples. |
| [`demo.py`](file:///Users/priyanshsmac/Developer/Projects/python/demo.py) | Full end-to-end demo running a Starlette server with simulated crashes. |
| [`design.md`](file:///Users/priyanshsmac/Developer/Projects/python/design.md) | In-depth technical specifications, schema definitions, and design decisions. |
| [`memory.md`](file:///Users/priyanshsmac/Developer/Projects/python/memory.md) | Development log tracking completed milestones and design notes. |
| [`phases.md`](file:///Users/priyanshsmac/Developer/Projects/python/phases.md) | Multi-phase development roadmap and feature checklist. |
| [`pyproject.toml`](file:///Users/priyanshsmac/Developer/Projects/python/pyproject.toml) | Package metadata, dependencies, build settings, and `pytest` config. |
| [`rules.md`](file:///Users/priyanshsmac/Developer/Projects/python/rules.md) | Engineering rules, security constraints (fail-silent), and coding standards. |

---

### Package Source (`src/agentic_sre/`)

#### Package Root
* [`__init__.py`](file:///Users/priyanshsmac/Developer/Projects/python/src/agentic_sre/__init__.py): Exposes public imports such as `AgenticSREMiddleware`.
* [`middleware.py`](file:///Users/priyanshsmac/Developer/Projects/python/src/agentic_sre/middleware.py): ASGI Middleware that intercepts unhandled HTTP 500 exceptions, immediately responds with JSON, and fires an asynchronous background investigation task.

#### `ai/` — Artificial Intelligence & RAG
* [`base.py`](file:///Users/priyanshsmac/Developer/Projects/python/src/agentic_sre/ai/base.py): Abstract base class defining the standard interface for AI analysis providers.
* [`gemini.py`](file:///Users/priyanshsmac/Developer/Projects/python/src/agentic_sre/ai/gemini.py): Implementation of Google Gemini AI provider for generating structured Root Cause Analysis (RCA).
* [`vector_store.py`](file:///Users/priyanshsmac/Developer/Projects/python/src/agentic_sre/ai/vector_store.py): ChromaDB-backed vector database for storing past crash RCAs and querying similar historical incidents.

#### `core/` — Extraction & Sanitization
* [`extractor.py`](file:///Users/priyanshsmac/Developer/Projects/python/src/agentic_sre/core/extractor.py): Extracts HTTP request context, headers, parameters, and formatted stack trace details from unhandled exceptions.
* [`sanitizer.py`](file:///Users/priyanshsmac/Developer/Projects/python/src/agentic_sre/core/sanitizer.py): Redacts sensitive user data, auth tokens, passwords, credit card numbers, and API keys before sending context to AI providers.

#### `notifications/` — Alerting & Webhook Integrations
* [`dispatcher.py`](file:///Users/priyanshsmac/Developer/Projects/python/src/agentic_sre/notifications/dispatcher.py): Coordinates asynchronous dispatch of alerts to configured channels without blocking application logic.
* [`webhooks.py`](file:///Users/priyanshsmac/Developer/Projects/python/src/agentic_sre/notifications/webhooks.py): Formats crash RCAs into rich visual embeds for Discord and Slack webhooks.

---

### `scratch/` — Local Experiments
* Contains standalone scratch scripts used during development to verify individual components (AI providers, sanitizer, notifications, vector store RAG pipeline) independently.

---

### `tests/` — Automated Test Suite
* [`test_middleware.py`](file:///Users/priyanshsmac/Developer/Projects/python/tests/test_middleware.py): Unit and integration tests for ASGI exception interception and background task trigger.
* [`test_sanitizer.py`](file:///Users/priyanshsmac/Developer/Projects/python/tests/test_sanitizer.py): Unit tests verifying regex-based PII and token redaction rules.
* [`test_vector_store.py`](file:///Users/priyanshsmac/Developer/Projects/python/tests/test_vector_store.py): Unit tests for ChromaDB storage, similarity search, and RAG retrieval.
