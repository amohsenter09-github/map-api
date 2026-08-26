import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api.health import router as health_router
from app.api.map import router as map_router
from app.api.pins import router as pins_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import close_db, init_db

STATIC_DIR = Path(__file__).resolve().parent / "static"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        await init_db()
    except Exception:
        logger.exception("Postgres is not reachable; GET /map still works, POST /pins will fail")
    yield
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(map_router)
    app.include_router(pins_router)

    @app.exception_handler(SQLAlchemyError)
    async def db_error(_request, _exc):
        logger.exception("Database error")
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    @app.get("/", include_in_schema=False)
    async def ui():
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        theme = (settings.ui_theme or "orange").strip().lower()
        if theme not in {"orange", "green"}:
            theme = "orange"
        html = html.replace('data-theme="orange"', f'data-theme="{theme}"', 1)
        if theme == "green":
            html = html.replace(">Map API<", ">Map API · production<")
            html = html.replace("<title>Map</title>", "<title>Map · production</title>")
        return HTMLResponse(html)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
