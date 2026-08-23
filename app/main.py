from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.map import router as map_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    app.include_router(map_router)

    @app.get("/")
    async def root():
        return {"service": settings.app_name}

    return app


app = create_app()
