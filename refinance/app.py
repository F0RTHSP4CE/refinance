"""FastAPI app initialization, exception handling"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from refinance.config import Config, get_config
from refinance.errors.base import ApplicationError
from refinance.routes.balance import balance_router
from refinance.routes.entity import entity_router
from refinance.routes.tag import tag_router
from refinance.routes.transaction import transaction_router

config: Config = get_config()
app = FastAPI(title=config.app_name, version=config.app_version)


@app.exception_handler(ApplicationError)
def application_exception_handler(request: Request, exc: ApplicationError):
    return JSONResponse(
        status_code=500, content={"error_code": exc.error_code, "error": exc.error}
    )


app.include_router(entity_router)
app.include_router(tag_router)
app.include_router(transaction_router)
app.include_router(balance_router)
