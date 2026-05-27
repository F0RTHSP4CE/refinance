"""API routes for deposit provider callbacks"""

from typing import Annotated
from uuid import UUID

from app.dependencies.services import (
    get_cryptapi_deposit_provider_service,
    get_stripe_authorization_service,
    get_stripe_deposit_provider_service,
    get_stripe_service,
)
from app.errors.common import NotFoundError
from app.schemas.deposit_providers.cryptapi import CryptAPICallbackSchema
from app.services.deposit_providers.cryptapi import CryptAPIDepositProviderService
from app.services.deposit_providers.stripe import StripeDepositProviderService
from app.services.stripe import StripeService
from app.services.stripe_authorization import StripeAuthorizationService
from fastapi import APIRouter, Body, Depends, Form, Header, HTTPException, Path, Request
from fastapi.responses import PlainTextResponse

deposit_provider_callbacks_router = APIRouter(
    prefix="/deposit-callbacks", tags=["DepositProvidersCallback"]
)


@deposit_provider_callbacks_router.post("/cryptapi/{deposit_uuid}")
def cryptapi_callback(
    deposit_uuid: Annotated[UUID, Path()],
    cryptapi_callback: CryptAPICallbackSchema = Form(),
    cryptapi_deposit_provider_service: CryptAPIDepositProviderService = Depends(
        get_cryptapi_deposit_provider_service
    ),
):
    cryptapi_deposit_provider_service.complete_deposit(
        deposit_uuid=deposit_uuid,
        cryptapi_callback=cryptapi_callback,
    )
    return PlainTextResponse("*ok*")


@deposit_provider_callbacks_router.post("/stripe")
async def stripe_callback(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    stripe_service: StripeService = Depends(get_stripe_service),
    stripe_deposit_provider_service: StripeDepositProviderService = Depends(
        get_stripe_deposit_provider_service
    ),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
):
    payload = await request.body()
    try:
        event = stripe_service.construct_webhook_event(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe webhook: {exc}")

    stripe_deposit_provider_service.handle_webhook_event(event)
    event_type = str(event.get("type") or "")
    data_object = (event.get("data") or {}).get("object") or {}
    if (
        event_type == "checkout.session.completed"
        and str(data_object.get("mode") or "") == "setup"
    ):
        stripe_authorization_service.handle_setup_session_completed(data_object)
    return PlainTextResponse("ok")
