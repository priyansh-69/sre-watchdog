# Developer Rules & Boundaries Document

## 1. Core Philosophy
The guiding principle of this project is **"Do No Harm."** As an observability middleware, this package will run inside a user's production server. It must *never* be the reason the host application fails, slows down, or leaks sensitive data.

## 2. Strict Library Boundaries
To keep the package lightweight and reduce conflict with the host application's dependencies, we strictly limit third-party libraries.

### Allowed Third-Party Libraries
- `google-genai`: Explicitly required for LLM interaction (do NOT use `langchain` or `llama_index` as they introduce too much bloat for a middleware package).
- `chromadb`: Required for local, serverless vector storage (do NOT use Pinecone, Qdrant, or Postgres-based vector DBs for this package to ensure one-click installation).
- `httpx`: Required for modern asynchronous HTTP requests to Slack/Discord.
- `fastapi` & `starlette`: Required only for typing and middleware subclassing.

### Strictly Forbidden Libraries
- `requests`: **BANNED.** It is synchronous and blocking. If `requests.post()` hangs while sending a Slack message, the entire host API will freeze. Always use `httpx` with `async/await`.
- Heavy ML Frameworks (`torch`, `tensorflow`): Absolutely forbidden. The host machine may not have the compute resources; all ML logic must stay on the Gemini API and ChromaDB.

## 3. Asynchronous Rules (Crucial)
Because we are building an ASGI middleware, async hygiene is critical.
1. **Never block the event loop:** Any network call (Gemini API, Webhooks) or disk I/O (ChromaDB queries) MUST be awaited.
2. **Fire and Forget:** The actual AI processing must occur *after* the HTTP response has been returned to the client. 
   - **Rule:** Use `asyncio.create_task()` or Starlette's `BackgroundTasks` to execute the AI logic. Do not await the AI response inside the main request-response cycle.

## 4. Error Handling Guidelines
If the AI Detective fails, the host application must survive.
1. **The Fail-Silent Rule:** If `agentic_sre` crashes (e.g., Gemini API is down, Slack webhook is invalid, API rate limits are hit), it must catch its own exception, log it locally to `stderr`, and terminate quietly. It must **never** bubble its own exceptions up to the host application.
2. **Timeouts:** All external API calls (`httpx` to Slack, calls to Gemini) MUST have strict, short timeouts (e.g., `timeout=5.0` seconds). The background task should die rather than hang indefinitely.

## 5. Security & Data Privacy (Redaction)
We are sending stack traces and local variables to an external LLM (Gemini). This is a massive security risk if not handled correctly.
1. **Regex Scrubbing:** Before the stack trace string leaves the server, it must pass through the `sanitizer.py` module.
2. **Mandatory Redactions:**
   - Any key matching `(?i)(password|secret|token|api_key|auth|bearer)` must have its value replaced with `[REDACTED]`.
   - Any string matching standard Credit Card or SSN regex patterns must be replaced with `[REDACTED]`.
3. **Opt-in Variables:** By default, local environment variables from the crashing frame should NOT be sent to the LLM unless explicitly allowed by the user via configuration.

## 6. AI & Prompt Engineering Boundaries
1. **Determinism:** When calling the Gemini API, set `temperature=0.1` to ensure analytical, repeatable root-cause reports rather than creative or hallucinatory responses.
2. **Structured Output:** The LLM prompt must enforce a strict JSON output schema. The AI should not return raw markdown directly; it must return JSON so our `dispatcher.py` can format the Slack message consistently every time.

## 7. Python Packaging Rules
1. **Dependencies:** Use `pyproject.toml`.
2. **Type Hinting:** 100% type hinting coverage is mandatory (use Python `typing` module). This ensures developers using IDEs like VSCode get intellisense when configuring the middleware.
3. **Docstrings:** Follow Google-style docstrings for every public class and function.
