from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from .api.routes import router as api_router
from .db.base import Base
from .db.session import engine
from .db import models  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Auto-create tables on startup if they do not exist.
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as exc:
        # Keep API booting in degraded mode; endpoints will return DB-specific errors.
        logger.exception("Database startup initialization failed: %s", exc)
    yield


app = FastAPI(
    title="Watchtower Orchestrator API",
    version="0.1.0",
    description="MVP API for lottery eligibility orchestration.",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
