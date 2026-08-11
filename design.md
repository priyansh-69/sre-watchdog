# Design & Formatting Specification (design.md)

## 1. Visual Identity & Theme
Even though `agentic-sre` is a backend Python package, visual design matters immensely for **Developer Experience (DX)**. The visual design applies to three distinct surfaces:
1. **Chat Notifications** (Slack Block Kit & Discord Embeds)
2. **Terminal Output** (Local CLI logging for debugging)
3. **GitHub & PyPI Documentation** (README branding)

---

## 2. Color Palette & Hierarchy

### Notification Sidebars & Accents
To enable immediate visual triaging by on-call engineers, alerts use standard operational status colors:

| State / Context | Hex Code | Purpose / Usage |
| :--- | :--- | :--- |
| **Critical Crash** | `#DC2626` (Red-600) | Primary alert border for `500` server errors and unhandled exceptions. |
| **AI Investigation** | `#9333EA` (Purple-600) | Accent for LLM root cause analysis section and agent reasoning blocks. |
| **RAG / Knowledge Match** | `#0284C7` (Sky-600) | Indicates historical error matches or matched repository documentation. |
| **Terminal / Success** | `#16A34A` (Green-600) | Used for middleware startup confirmation and health check logs. |

---

## 3. Slack Notification Layout (Block Kit Specification)

The Slack message must present information in strict order of developer priority: **What broke -> Why it broke -> How to fix it -> Context.**

### Structural Hierarchy

```text
🔴 [CRITICAL CRASH] FastAPI 500 Internal Server Error
────────────────────────────────────────────────────
📍 Endpoint: POST /api/v1/checkout
💥 Exception: KeyError: 'discount_code'
📁 File: app/routers/checkout.py:84

🧠 AI Root Cause Analysis
"The request body was missing the 'discount_code' key. The endpoint attempted 
to access payload['discount_code'] directly without validation or a fallback."

💡 Suggested Fix
```python
# Change line 84 from:
discount = payload["discount_code"]

# To:
discount = payload.get("discount_code", None)
```

📚 Related Documentation (RAG Context)
• docs/checkout_flow.md (Similarity Match: 88%)
────────────────────────────────────────────────────
⏱️ Analyzed in 1.2s via Gemini 1.5 Flash • Agentic-SRE v0.1.0
```

### Formatting Rules for Chat Messages
1. **Code Blocks:** Stack traces, inline file paths (`app/main.py:42`), and code diff suggestions MUST always be wrapped in markdown code blocks (` ```python `) for readability.
2. **Emojis:** Used strictly for section anchors (`🔴` Alert, `🧠` AI Analysis, `💡` Fix, `📚` RAG Context, `⏱️` Metrics). Do not overuse decorative emojis.
3. **Length Restrictions:** The AI summary must be constrained to maximum 3 sentences. Long-winded summaries slow down incident triage.

---

## 4. Terminal / CLI Logging Design

When running locally in development mode, the package uses standard ANSI colors (or the `rich` library) for terminal logging:

- **Middleware Init:** `[INFO] AgenticSREMiddleware attached to FastAPI app [GREEN]`
- **Crash Intercepted:** `[CRASH] Intercepted 500 Error on /checkout. Spawning AI background task... [RED]`
- **Sanitizer Alert:** `[SECURITY] Redacted 2 API Keys and 1 Bearer Token from trace [YELLOW]`
- **Dispatch Complete:** `[DISPATCH] Sent RCA report to Slack in 840ms [PURPLE]`

---

## 5. Typography & Documentation Style

### Markdown Rules for README & Docs
- **Font Stack:** Standard GitHub Sans / Monospace for code snippets.
- **Header Structure:** Use explicit H1 (`#`) for project title, H2 (`##`) for major sections, H3 (`###`) for sub-components.
- **Callout Quotes:** Use GitHub GitHub-Flavored Markdown callouts for important developer notes:
  > **[!IMPORTANT]**
  > Ensure `GEMINI_API_KEY` and `SLACK_WEBHOOK_URL` are set in your environment variables before starting the host application.
