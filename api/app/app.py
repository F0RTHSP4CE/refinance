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
from app.routes.fee import router as fee_router
from app.routes.invoice import invoice_router
from app.routes.pos import pos_router
from app.routes.split import split_router
from app.routes.stats import router as stats_router
from app.routes.tag import tag_router
from app.routes.token import token_router
from app.routes.transaction import transaction_router
from app.routes.treasury import treasury_router
from app.services.token import TokenService
from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO)

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
def database_exception_handler(request: Request, exc: SQLAlchemyError):
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
app.include_router(invoice_router)
app.include_router(split_router)
app.include_router(currency_exchange_router)
app.include_router(pos_router)
# DISABLED DUE TO CRYPTAPI BUGS
# app.include_router(deposits_router)
# app.include_router(deposit_provider_callbacks_router)
app.include_router(fee_router)
app.include_router(stats_router)
app.include_router(treasury_router)


@app.middleware("http")
async def log_non_get_requests(request: Request, call_next):
    """Log all non-GET requests and append actor id from JWT."""
    if request.method != "GET":
        # Read and log request body
        body = await request.body()
        # Decode raw bytes
        try:
            raw_str = body.decode("utf-8")
        except Exception:
            raw_str = str(body)
        # If JSON, re-dump to preserve Unicode
        try:
            parsed = json.loads(raw_str)
            body_str = json.dumps(parsed, ensure_ascii=False)
        except Exception:
            body_str = raw_str
        token = request.headers.get("x-token")
        actor_id = None
        if token:
            try:
                actor_id = TokenService.decode_entity_id_from_token(
                    token, config.secret_key or ""
                )
            except TokenInvalid:
                actor_id = None
        logger.info(
            f"{request.method} {request.url.path} actor_id={actor_id} {body_str}"
        )

        # Replay the request body to downstream handlers
        async def receive() -> dict:
            return {"type": "http.request", "body": body}

        response = await call_next(Request(request.scope, receive))
        if actor_id is not None:
            response.headers["X-Actor-Id"] = str(actor_id)
        return response
    return await call_next(request)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
