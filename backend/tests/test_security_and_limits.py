import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.core.security import rate_limiter

@pytest.mark.asyncio
async def test_security_rate_limiting_and_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Health check should be open
        health = await ac.get("/health")
        assert health.status_code == 200

        # 2. Rate limiting test
        rate_limiter.reset()
        original_limit = rate_limiter.limit
        rate_limiter.limit = 3 # Temporarily set small limit for testing

        dummy_payload = {
            "domain": "test-limits.org",
            "tab_url": "https://test-limits.org",
            "requests": [],
            "storage_keys": [],
            "permissions": []
        }

        try:
            # 3 allowed requests
            for _ in range(3):
                res = await ac.post("/api/v1/observations/ingest", json=dummy_payload)
                assert res.status_code == 200

            # 4th request should trigger 429 Too Many Requests
            exceeded = await ac.post("/api/v1/observations/ingest", json=dummy_payload)
            assert exceeded.status_code == 429
            assert "Rate limit exceeded" in exceeded.json()["detail"]
        finally:
            rate_limiter.reset()
            rate_limiter.limit = original_limit

        # 3. Payload size limit test
        huge_headers = {"content-length": str(15 * 1024 * 1024)} # 15MB > 10MB limit
        payload_res = await ac.post(
            "/api/v1/observations/ingest",
            json=dummy_payload,
            headers=huge_headers
        )
        assert payload_res.status_code == 413
        assert "exceeds maximum allowed size" in payload_res.json()["detail"]

@pytest.mark.asyncio
async def test_api_key_authentication_enforcement():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        original_require = settings.require_api_key
        original_key = settings.api_key
        settings.require_api_key = True
        settings.api_key = "test_secret_key_123"

        dummy_payload = {
            "domain": "test-auth.org",
            "tab_url": "https://test-auth.org",
            "requests": [],
            "storage_keys": [],
            "permissions": []
        }

        try:
            # Request without API key should fail with 401
            unauth = await ac.post("/api/v1/observations/ingest", json=dummy_payload)
            assert unauth.status_code == 401

            # Request with wrong API key should fail with 401
            wrong_auth = await ac.post(
                "/api/v1/observations/ingest",
                json=dummy_payload,
                headers={"X-API-Key": "wrong_key"}
            )
            assert wrong_auth.status_code == 401

            # Request with valid X-API-Key should succeed
            valid_auth = await ac.post(
                "/api/v1/observations/ingest",
                json=dummy_payload,
                headers={"X-API-Key": "test_secret_key_123"}
            )
            assert valid_auth.status_code == 200

            # Request with valid Bearer token should succeed
            bearer_auth = await ac.post(
                "/api/v1/observations/ingest",
                json=dummy_payload,
                headers={"Authorization": "Bearer test_secret_key_123"}
            )
            assert bearer_auth.status_code == 200
        finally:
            settings.require_api_key = original_require
            settings.api_key = original_key
