from fastapi import FastAPI

from app.api.middleware import TimeoutMiddleware, register_error_handlers
from app.api.routes import router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(TimeoutMiddleware, timeout_seconds=settings.REQUEST_TIMEOUT_SECONDS)
    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()

