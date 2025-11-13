from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager, suppress
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import sessionmanager
import fastapi.openapi.utils as fu
from .settings import get_settings
from fastapi import FastAPI
from pathlib import Path
from . import errors


def create_app(init_db: bool = True) -> FastAPI:
    settings = get_settings()
    lifespan = None

    # SQLAlchemy initialization process
    if init_db:
        sessionmanager.init(settings.database.endpoint)

        @asynccontextmanager
        async def lifespan(_: FastAPI):
            yield
            with suppress(Exception):
                await sessionmanager.close()

    fu.validation_error_response_definition = errors.ErrorResponse.model_json_schema()

    app = FastAPI(
        title="API Docs",
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Blocks"},
            {"name": "Transactions"},
            {"name": "Addresses"},
            {"name": "Wallet"},
            {"name": "Holders"},
            {"name": "Tokens"},
            {"name": "General"},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(errors.Abort, errors.abort_handler)
    app.add_exception_handler(
        RequestValidationError,
        errors.validation_handler,
    )

    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        "Static media",
    )

    from .transactions import router as db_router
    from .address import router as address_router
    from .general import router as general_router
    from .blocks import router as blocks_router
    from .wallet import router as wallet_router
    from .holders import router as holders_router
    from .token import router as token_router

    app.include_router(token_router)
    app.include_router(holders_router)
    app.include_router(address_router)
    app.include_router(general_router)
    app.include_router(blocks_router)
    app.include_router(wallet_router)
    app.include_router(db_router)

    @app.get("/ping")
    async def ping_pong():
        return "pong"

    return app
