import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.api.routes import ingest, query
from app.core.config import settings
from app.models.schemas import HealthResponse

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ── Sentry (non-local only, mirrors template) ─────────────────────────────────

if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    import sentry_sdk

    sentry_sdk.init(
        dsn=str(settings.SENTRY_DSN),
        environment=settings.ENVIRONMENT,
        enable_tracing=True,
    )
    logger.info("Sentry initialised")


# ── OpenAPI unique-id generator (mirrors template) ────────────────────────────

def generate_unique_id(route: APIRoute) -> str:
    """Produce clean, collision-free operation IDs for the OpenAPI schema."""
    return f"{route.tags[0]}-{route.name}" if route.tags else route.name


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CodeContext API starting up…")
    yield
    logger.info("CodeContext API shutting down…")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RAG/MCP system for codebase understanding",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=generate_unique_id,
    lifespan=lifespan,
)

# CORS — driven by settings, not hardcoded "*"
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Routers
app.include_router(ingest.router, prefix=settings.API_V1_STR, tags=["ingest"])
app.include_router(query.router,  prefix=settings.API_V1_STR, tags=["query"])


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict:
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    from pathlib import Path

    db_ok = Path(settings.CHROMA_DB_PATH).exists() if settings.CHROMA_PERSIST else True
    return HealthResponse(status="ok", db_connected=db_ok)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )
