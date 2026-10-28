import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status
from app.config import settings

class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter per client key/IP."""
    def __init__(self, limit_per_minute: int = 120):
        self.limit = limit_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        window_start = now - 60.0
        
        # Purge timestamps older than 60 seconds
        recent = [t for t in self.requests[client_id] if t > window_start]
        self.requests[client_id] = recent

        if len(recent) >= self.limit:
            return False

        self.requests[client_id].append(now)
        return True

    def reset(self):
        self.requests.clear()

rate_limiter = SlidingWindowRateLimiter(limit_per_minute=settings.rate_limit_per_minute)

async def verify_security_access(request: Request) -> Optional[str]:
    """
    Validates loopback restrictions, API keys, payload quotas, and rate limits.
    """
    client_host = request.client.host if request.client else "127.0.0.1"

    # 1. Loopback-only enforcement
    is_loopback = client_host in ("127.0.0.1", "localhost", "::1", "testclient")
    if settings.enforce_loopback_only and not is_loopback:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: PrivacyLens backend is restricted to loopback connections (127.0.0.1)."
        )

    # 2. Authentication check
    if settings.require_api_key or settings.api_key:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header.split(" ", 1)[1]

        if not api_key or api_key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Valid X-API-Key or Bearer token is required."
            )

    # 3. Payload size check
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            length_bytes = int(content_length)
            if length_bytes > settings.max_payload_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Payload exceeds maximum allowed size of {settings.max_payload_bytes} bytes."
                )
        except ValueError:
            pass

    # 4. Rate limit check
    client_id = client_host
    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.rate_limit_per_minute} requests per minute."
        )

    return client_host
