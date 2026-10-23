from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.core.policy_fetcher import PolicyFetchError, PublicResolver, normalize_policy_url


def test_storage_inspector_never_reads_values_or_cookie_names():
    source = Path(__file__).parents[2] / "extension" / "src" / "content" / "storage-inspector.ts"
    text = source.read_text(encoding="utf-8")
    assert ".getItem(" not in text
    assert ".key(" not in text
    assert "document.cookie" not in text
    assert "window.localStorage.length" in text
    assert "window.sessionStorage.length" in text


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.com/privacy",
    "http://localhost/privacy", "http://127.0.0.1/privacy",
    "http://10.1.2.3/privacy", "http://169.254.169.254/latest/meta-data",
    "http://[::1]/privacy", "https://user:pass@example.com/privacy",
    "https://example.com:8443/privacy", "http://2130706433/privacy",
])
def test_policy_url_rejects_unsafe_destinations(url):
    with pytest.raises(PolicyFetchError):
        normalize_policy_url(url)


def test_policy_url_removes_fragment_but_keeps_fetch_query():
    assert normalize_policy_url("https://example.com/privacy?lang=en#section") == "https://example.com/privacy?lang=en"


@pytest.mark.asyncio
async def test_resolver_rejects_private_dns_answer(monkeypatch):
    class FakeLoop:
        async def getaddrinfo(self, *args, **kwargs):
            return [(2, 1, 6, "", ("127.0.0.1", 443))]

    monkeypatch.setattr("asyncio.get_running_loop", lambda: FakeLoop())
    with pytest.raises(PolicyFetchError, match="non-public"):
        await PublicResolver().resolve("public.example", 443)
