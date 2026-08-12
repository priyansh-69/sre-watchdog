# 🤖 Agentic-SRE

> **Autonomous, LLM-Agnostic Observability & AI Bug Detective Middleware for Python Backends**

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Framework: FastAPI / Starlette](https://img.shields.io/badge/framework-FastAPI%20%7C%20Starlette-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Agentic-SRE** is a lightweight, zero-latency ASGI middleware that intercepts unhandled `500 Internal Server Error` crashes in FastAPI and Starlette applications. 

When a backend crash occurs, `agentic-sre` instantly returns the HTTP response to the client, while spawning a non-blocking background task that scrubs sensitive PII, cross-references historical fixes using local RAG vector memory (ChromaDB), performs root-cause analysis via AI (Google Gemini), and delivers actionable fix reports directly to **Slack** or **Discord**.
