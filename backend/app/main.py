from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import realtime, trainings, tutorials
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
app.include_router(realtime.router, prefix="/api/v1")
app.include_router(tutorials.router, prefix="/api/v1")

ASSETS_DIR = STATIC_DIR / "assets"
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    """生产模式统一从后端地址提供 React，并支持前端路由刷新。"""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="接口不存在")
    requested = (STATIC_DIR / full_path).resolve()
    static_root = STATIC_DIR.resolve()
    if full_path and requested.is_file() and static_root in requested.parents:
        return FileResponse(requested)
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="前端尚未构建")
    return FileResponse(index)
