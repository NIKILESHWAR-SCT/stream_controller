import logging
from fastapi import FastAPI
from api.stream import router as stream_router
from db.session import init_db

logger = logging.getLogger("streaming_controller")
logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(title="streaming_controller")

    app.include_router(stream_router)

    @app.on_event("startup")
    async def on_startup():
        logger.info("Starting streaming_controller, initializing DB")
        await init_db()

    return app


app = create_app()
