"""FastAPI app initialization, exception handling"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from refinance.config import Config, get_config
from refinance.errors.base import ApplicationError
from refinance.routes.balance import balance_router
from refinance.routes.entity import entity_router
from refinance.routes.tag import tag_router
from refinance.routes.token import token_router
from refinance.routes.transaction import transaction_router

config: Config = get_config()
app = FastAPI(title=config.app_name, version=config.app_version)


@app.exception_handler(ApplicationError)
def application_exception_handler(request: Request, exc: ApplicationError):

    return JSONResponse(
        status_code=exc.http_code or 418,
        content={
            "error_code": exc.error_code,
            "error": exc.error,
            "where": exc.where,
        },
    )


@app.exception_handler(SQLAlchemyError)
def sqlite_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=418,
        content={"error_code": 4000, "error": exc._message()},
    )


app.include_router(token_router)
app.include_router(entity_router)
app.include_router(tag_router)
app.include_router(transaction_router)
app.include_router(balance_router)
