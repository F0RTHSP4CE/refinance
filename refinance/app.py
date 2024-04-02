"""FastAPI app initialization, exception handling"""

from fastapi import FastAPI

from refinance.config import Config, get_config
from refinance.errors.handler import regiter_exception_handlers
from refinance.routes.entity import entity_router


def app_factory(*, config: Config | None = None) -> FastAPI:
    config: Config = config or get_config()
    app = FastAPI(title=config.app_name, version=config.app_version)
    regiter_exception_handlers(app)
    app.include_router(entity_router)
    app.dependency_overrides[get_config] = lambda: config
    return app
