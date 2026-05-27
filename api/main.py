"""FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import tasks, tools, health
import structlog

log = structlog.get_logger()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Autonomous AI OS",
        description="Self-evolving AI platform with Supabase",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(tasks.router)
    app.include_router(tools.router)
    app.include_router(health.router)

    @app.on_event("startup")
    async def startup():
        log.info("api.startup", message="Autonomous AI OS online")

    return app


app = create_app()
