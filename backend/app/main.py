from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import init_db
from app.core.security import verify_security_access
from app.api.routes_policies import router as policies_router
from app.api.routes_observations import router as observations_router
from app.api.routes_sites import router as sites_router
from app.api.routes_evidence import router as evidence_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema and run pending migrations on startup
    await init_db()
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Evidence-driven browser privacy intelligence system correlating declared policies with runtime telemetry.",
    lifespan=lifespan
)

# CORS configuration allowing requests from Chrome extensions and local dev environments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routes protected by security verification (loopback check, rate limiter, auth)
security_dependency = [Depends(verify_security_access)]
app.include_router(policies_router, prefix="/api/v1", dependencies=security_dependency)
app.include_router(observations_router, prefix="/api/v1", dependencies=security_dependency)
app.include_router(sites_router, prefix="/api/v1", dependencies=security_dependency)
app.include_router(evidence_router, prefix="/api/v1", dependencies=security_dependency)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "ai_provider": settings.default_ai_provider,
        "loopback_only": settings.enforce_loopback_only,
        "auth_enabled": bool(settings.api_key or settings.require_api_key)
    }

if __name__ == "__main__":
    import uvicorn
    # Enforce loopback binding by default for companion deployment security
    bind_host = "127.0.0.1" if settings.enforce_loopback_only else "0.0.0.0"
    uvicorn.run("app.main:app", host=bind_host, port=8000, reload=True)
