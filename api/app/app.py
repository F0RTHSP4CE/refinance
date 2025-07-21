"""FastAPI app initialization, exception handling"""

import json
import logging
import traceback

import uvicorn
from app.config import Config, get_config
from app.errors.base import ApplicationError
from app.errors.token import TokenInvalid
from app.routes.balance import balance_router
from app.routes.currency_exchange import currency_exchange_router
from app.routes.deposit_provider_callbacks import deposit_provider_callbacks_router
from app.routes.deposits import deposits_router
from app.routes.entity import entity_router
from app.routes.oidc import router as oidc_router
from app.routes.resident_fee import router as resident_fee_router
from app.routes.split import split_router
from app.routes.stats import router as stats_router
from app.routes.tag import tag_router
from app.routes.token import token_router
from app.routes.transaction import transaction_router
from app.routes.treasury import treasury_router
from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware

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
app.add_middleware(
    SessionMiddleware,
    secret_key=config.secret_key,
)
if not config.secret_key:
    raise ValueError(
        "SECRET_KEY is missing in the configuration. Please set a valid secret key."
    )


@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(
    request: Request, exc: ResponseValidationError
):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Response validation error encountered",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(ApplicationError)
def application_exception_handler(request: Request, exc: ApplicationError):
    c = {
        "error_code": exc.error_code,
        "error": exc.error,
        "where": exc.where,
    }
    logger.error(c)
    # Only print full traceback when in debug logging
    if logger.isEnabledFor(logging.DEBUG):
        traceback.print_exception(exc)
    e = JSONResponse(
        status_code=exc.http_code or 418,
        content=c,
    )
    return e


@app.exception_handler(SQLAlchemyError)
def sqlite_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(exc)
    # Only print full traceback when in debug logging
    if logger.isEnabledFor(logging.DEBUG):
        traceback.print_exception(exc)
    e = JSONResponse(
        status_code=418,
        content={"error_code": 1500, "error": exc._message()},
    )
    return e


app.include_router(token_router)
app.include_router(entity_router)
app.include_router(tag_router)
app.include_router(transaction_router)
app.include_router(balance_router)
app.include_router(split_router)
app.include_router(currency_exchange_router)
app.include_router(deposits_router)
app.include_router(deposit_provider_callbacks_router)
app.include_router(resident_fee_router)
app.include_router(stats_router)
app.include_router(treasury_router)
app.include_router(oidc_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
