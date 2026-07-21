"""FastAPI application entry point for the Defense AI LMS POC."""

import logging
from contextlib import asynccontextmanager

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.components.analytics.router import router as analytics_router
from app.components.audit.router import router as audit_router
from app.components.auth.router import router as auth_router
from app.components.auth.service import AuthService
from app.components.catalog.router import router as catalog_router
from app.components.certificates.router import router as certificates_router
from app.components.chatbot.router import router as chatbot_router
from app.components.course_generation.router import router as course_generation_router
from app.components.enrolment.router import router as enrolment_router
from app.components.ingestion.router import router as ingestion_router
from app.components.learning.router import router as learning_router
from app.components.models3d.router import router as models3d_router
from app.components.quiz.router import router as quiz_router
from app.components.review.router import router as review_router
from app.core.config import settings
from app.database import async_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import all db_models so their tables register on Base.metadata before create_all.
    from app.database import Base, engine
    from app.components.auth import db_models  # noqa: F401
    from app.components.ingestion import db_models as _ingestion_models  # noqa: F401
    from app.components.content import db_models as _content_models  # noqa: F401
    from app.components.enrolment import db_models as _enrolment_models  # noqa: F401
    from app.components.chatbot import db_models as _chatbot_models  # noqa: F401
    from app.components.quiz import db_models as _quiz_models  # noqa: F401
    from app.components.audit import db_models as _audit_models  # noqa: F401
    from app.components.models3d import db_models as _models3d_models  # noqa: F401
    from app.components.certificates import db_models as _cert_models  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database initialization failed: %s", exc)

    try:
        async with async_session() as db:
            await AuthService.bootstrap_admin(db)
            from app.components.models3d.seed import seed_models

            await seed_models(db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Startup seeding failed: %s", exc)

    # The in-memory vector index lives in this process and is empty after a
    # restart — rebuild it from published courses so the chatbot works. Skipped
    # for Qdrant (persistent) and if no AI provider is configured for embeddings.
    if settings.VECTOR_BACKEND.lower() == "memory":
        try:
            from app.components.chatbot.sync_service import SyncService
            from app.gateway import get_gateway

            async with async_session() as db:
                stats = await SyncService.rebuild_published(get_gateway(), db)
            logger.info("Chatbot index rebuilt: %s", stats)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chatbot index rebuild skipped (%s): %s", type(exc).__name__, exc)

    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")] or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "model_provider": settings.MODEL_PROVIDER}


# Serve locally-stored assets (3D models, uploads) with NO external CDN — the
# air-gap requirement. The 3D viewer loads GLBs from /media/models3d/<key>.glb.
_media_dir = os.path.abspath(settings.LOCAL_STORAGE_PATH)
os.makedirs(_media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=_media_dir), name="media")


app.include_router(auth_router)
app.include_router(ingestion_router)
app.include_router(course_generation_router)
app.include_router(review_router)
app.include_router(catalog_router)
app.include_router(enrolment_router)
app.include_router(learning_router)
app.include_router(chatbot_router)
app.include_router(quiz_router)
app.include_router(analytics_router)
app.include_router(audit_router)
app.include_router(models3d_router)
app.include_router(certificates_router)
