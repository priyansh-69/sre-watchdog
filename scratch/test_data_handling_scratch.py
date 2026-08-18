import sys
sys.path.insert(0, "src")

from agentic_sre.core.sanitizer import Sanitizer
from agentic_sre.core.extractor import Extractor
from starlette.requests import Request
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient
from agentic_sre import AgenticSREMiddleware


def test_sanitizer():
    sanitizer = Sanitizer()

    # 1. Bearer Token
    raw_bearer = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature"
    redacted_bearer = sanitizer.redact(raw_bearer)
    print("Bearer Test:", redacted_bearer)
    assert "[REDACTED]" in redacted_bearer
    assert "eyJhbGciOiJIUzI1NiJ9" not in redacted_bearer

    # 2. API Key / Password
    raw_kv = "Config: api_key='sk-1234567890abcdef' password=\"supersecret123\""
    redacted_kv = sanitizer.redact(raw_kv)
    print("KV Test:", redacted_kv)
    assert "sk-1234567890abcdef" not in redacted_kv
    assert "supersecret123" not in redacted_kv

    # 3. Credit Card
    raw_cc = "Payment failed for card 4532-0154-9871-2345"
    redacted_cc = sanitizer.redact(raw_cc)
    print("CC Test:", redacted_cc)
    assert "4532-0154-9871-2345" not in redacted_cc
    assert "[REDACTED]" in redacted_cc

    # 4. Email
    raw_email = "Contact user at john.doe@example.com for info"
    redacted_email = sanitizer.redact(raw_email)
    print("Email Test:", redacted_email)
    assert "john.doe@example.com" not in redacted_email
    assert "[REDACTED]" in redacted_email

    # 5. Dict Sanitization
    headers = {
        "Authorization": "Bearer token123",
        "X-Api-Key": "my-secret-key",
        "User-Agent": "Mozilla/5.0",
        "X-User-Email": "alice@test.com"
    }
    sanitizer_dict = sanitizer.sanitize_dict(headers)
    print("Sanitized Dict:", sanitizer_dict)
    assert sanitizer_dict["Authorization"] == "[REDACTED]"
    assert sanitizer_dict["X-Api-Key"] == "[REDACTED]"
    assert sanitizer_dict["User-Agent"] == "Mozilla/5.0"
    print("Sanitizer Unit Tests PASSED!\n")


async def crashing_endpoint(request):
    raise RuntimeError("Failed processing secret_key='shhh' for user dev@company.com")


app = Starlette(routes=[Route("/crash", crashing_endpoint)])
app.add_middleware(AgenticSREMiddleware)


def test_extractor_and_middleware():
    client = TestClient(app, raise_server_exceptions=False)
    headers = {
        "Authorization": "Bearer my-secret-token",
        "x-api-key": "secret-api-key-value",
        "user-agent": "test-client"
    }
    res = client.get("/crash", headers=headers)
    assert res.status_code == 500
    print("Middleware Test PASSED!\n")


if __name__ == "__main__":
    test_sanitizer()
    test_extractor_and_middleware()
