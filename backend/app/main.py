from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import trainings
from .core.errors import AppError
from .db import SessionLocal, engine, run_migrations
from .models import Base, Training
from .services.content_library import ContentLibraryError

STATIC_DIR = Path(__file__).parent / "static"


def _recover_stale_tasks():
    db = SessionLocal()
    try:
        for t in (
            db.query(Training)
            .filter(Training.status.in_(("transcribing", "analyzing")))
            .all()
        ):
            t.status = "failed"
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    _recover_stale_tasks()
    yield


app = FastAPI(title="AI 主播陪练", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(ContentLibraryError)
async def content_library_error_handler(request: Request, exc: ContentLibraryError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "CONTENT_LIBRARY_ERROR", "message": str(exc)}},
    )


app.include_router(trainings.router, prefix="/api/v1")
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
