"""FastAPI app initialization, exception handling"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from refinance.config import config
from refinance.errors.base import ApplicationError
from refinance.routes.entity import entity_router

app = FastAPI(title=config.app_name)


@app.exception_handler(ApplicationError)
def application_exception_handler(request: Request, exc: ApplicationError):
    return JSONResponse(
        status_code=500, content={"error_code": exc.error_code, "error": exc.error}
    )


app.include_router(entity_router)
