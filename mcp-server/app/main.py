import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.middleware import TimeoutMiddleware, register_error_handlers
from app.api.routes import router
from app.core.config import settings
from app.infrastructure.db.session import engine

logger = logging.getLogger(__name__)


async def _init_db() -> None:
    try:
        import os
        init_sql_path = os.path.join(os.path.dirname(__file__), "..", "init.sql")
        if not os.path.exists(init_sql_path):
            logger.warning("init.sql not found, skipping DB init")
            return
        with open(init_sql_path) as f:
            sql = f.read()
        async with engine.begin() as conn:
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    try:
                        await conn.execute(text(stmt))
                    except Exception as e:
                        logger.debug("DB init statement skipped: %s", e)
        logger.info("DB init completed")
    except Exception as e:
        logger.error("DB init failed: %s", e)


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

    @app.on_event("startup")
    async def startup():
        await _init_db()

    @app.get("/health", tags=["system"], summary="Health check")
    async def health():
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception as e:
            db_status = f"error: {e}"

        return JSONResponse({
            "status": "ok" if db_status == "ok" else "degraded",
            "database": db_status,
            "service": settings.APP_NAME,
        })

    @app.get("/demo", include_in_schema=False)
async def demo():
    return FileResponse("demo_orange.html")

    return app

app = create_app()
