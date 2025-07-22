"""API routes for deposit provider callbacks"""

from typing import Annotated
from uuid import UUID

from app.errors.common import NotFoundError
from app.schemas.deposit_providers.cryptapi import CryptAPICallbackSchema
from app.services.deposit_providers.cryptapi import CryptAPIDepositProviderService
from fastapi import APIRouter, Body, Depends, Form, Path
from fastapi.responses import PlainTextResponse

deposit_provider_callbacks_router = APIRouter(
    prefix="/deposit-callbacks", tags=["DepositProvidersCallback"]
)


@deposit_provider_callbacks_router.post("/cryptapi/{deposit_uuid}")
def cryptapi_callback(
    deposit_uuid: Annotated[UUID, Path()],
    cryptapi_callback: CryptAPICallbackSchema = Form(),
    cryptapi_deposit_provider_service: CryptAPIDepositProviderService = Depends(),
):
    cryptapi_deposit_provider_service.complete_deposit(
        deposit_uuid=deposit_uuid,
        cryptapi_callback=cryptapi_callback,
    )
    return PlainTextResponse("*ok*")
