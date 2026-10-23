from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.db.database import init_db
from app.api.routes_policies import router as policies_router
from app.api.routes_observations import router as observations_router
from app.api.routes_sites import router as sites_router
from app.api.routes_evidence import router as evidence_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_deployment()
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Evidence-driven browser privacy intelligence using local browser signals.",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def bounded_request_body(request: Request, call_next):
    """Reject oversized/chunked bodies before Pydantic parsing or endpoint work."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.max_request_bytes:
                return JSONResponse({"detail": "Request body exceeds the size limit"}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)

    body = bytearray()
    more = True
    while more:
        message = await request.receive()
        chunk = message.get("body", b"")
        body.extend(chunk)
        if len(body) > settings.max_request_bytes:
            return JSONResponse({"detail": "Request body exceeds the size limit"}, status_code=413)
        more = message.get("more_body", False)

    queued = deque([{"type": "http.request", "body": bytes(body), "more_body": False}])

    async def replay_receive():
        if queued:
            return queued.popleft()
        return {"type": "http.request", "body": b"", "more_body": False}

    request._receive = replay_receive
    return await call_next(request)


app.include_router(policies_router, prefix="/api/v1")
app.include_router(observations_router, prefix="/api/v1")
app.include_router(sites_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "ai_provider": settings.default_ai_provider,
        "mode": settings.deployment_mode,
    }


if __name__ == "__main__":
    import uvicorn
    settings.validate_deployment()
    uvicorn.run("app.main:app", host=settings.bind_host, port=8000, reload=settings.debug)
