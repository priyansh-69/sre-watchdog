"""Async integration unit tests for AgenticSREMiddleware."""

from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from agentic_sre.middleware import AgenticSREMiddleware


async def healthy_route(request):
    return PlainTextResponse("OK")


async def crashing_route(request):
    raise ValueError("Simulated database failure")


def create_test_app():
    app = Starlette(
        routes=[
            Route("/ok", healthy_route),
            Route("/crash", crashing_route),
        ]
    )
    app.add_middleware(AgenticSREMiddleware)
    return app


def test_middleware_healthy_route():
    app = create_test_app()
    client = TestClient(app)
    response = client.get("/ok")
    assert response.status_code == 200
    assert response.text == "OK"


@patch("agentic_sre.middleware.GeminiProvider.analyze_error", new_callable=AsyncMock)
@patch("agentic_sre.middleware.dispatch_alerts", new_callable=AsyncMock)
def test_middleware_intercept_500(mock_dispatch, mock_analyze):
    mock_analyze.return_value = {
        "error_summary": "Test summary",
        "root_cause_hypothesis": "Test hypothesis",
        "failing_component": "test.py:10",
        "suggested_fix": "fix()",
    }
    mock_dispatch.return_value = None

    app = create_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/crash")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "Internal Server Error"
    assert "Agentic-SRE" in data["error"]
