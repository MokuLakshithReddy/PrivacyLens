from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import init_db
from app.api.routes_policies import router as policies_router
from app.api.routes_observations import router as observations_router
from app.api.routes_sites import router as sites_router
from app.api.routes_evidence import router as evidence_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema on startup
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

# Include API v1 routes
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
        "ai_provider": settings.default_ai_provider
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
