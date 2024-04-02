from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from refinance.errors.base import ApplicationError


def application_exception_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error_code": exc.error_code, "error": exc.error})


def regiter_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_exception_handler)  # type: ignore[arg-type]
