"""FastAPI app initialization, exception handling"""

import logging

from app.config import Config, get_config
from app.errors.base import ApplicationError
from app.routes.balance import balance_router
from app.routes.entity import entity_router
from app.routes.tag import tag_router
from app.routes.token import token_router
from app.routes.transaction import transaction_router
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

config: Config = get_config()
app = FastAPI(title=config.app_name, version=config.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApplicationError)
def application_exception_handler(request: Request, exc: ApplicationError):
    e = JSONResponse(
        status_code=exc.http_code or 418,
        content={
            "error_code": exc.error_code,
            "error": exc.error,
            "where": exc.where,
        },
    )
    logger.warning(e.body.decode())
    return e


@app.exception_handler(SQLAlchemyError)
def sqlite_exception_handler(request: Request, exc: SQLAlchemyError):
    e = JSONResponse(
        status_code=418,
        content={"error_code": 4000, "error": exc._message()},
    )
    logger.warning(e.body.decode())
    return e


app.include_router(token_router)
app.include_router(entity_router)
app.include_router(tag_router)
app.include_router(transaction_router)
app.include_router(balance_router)
