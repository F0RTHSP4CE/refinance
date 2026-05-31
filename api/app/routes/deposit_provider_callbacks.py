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


def _handle_subscription_deleted(
    subscription_obj: dict,
    stripe_authorization_service: StripeAuthorizationService,
) -> None:
    """Deactivate a StripeAuthorization when its Stripe subscription is cancelled."""
    subscription_id = str(subscription_obj.get("id") or "").strip()
    if not subscription_id:
        return
    from app.models.stripe_authorization import (  # avoid circular import at module level
        StripeAuthorization,
    )

    auth = (
        stripe_authorization_service.db.query(StripeAuthorization)
        .filter(StripeAuthorization.stripe_subscription_id == subscription_id)
        .first()
    )
    if auth and auth.active:
        import datetime

        auth.active = False
        auth.modified_at = datetime.datetime.now()
        stripe_authorization_service.db.flush()


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
    session_mode = str(data_object.get("mode") or "")
    if event_type == "checkout.session.completed" and session_mode in (
        "setup",
        "subscription",
    ):
        stripe_authorization_service.handle_setup_session_completed(data_object)
    elif event_type == "invoice.paid":
        stripe_authorization_service.handle_subscription_invoice_paid(data_object)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data_object, stripe_authorization_service)
    return PlainTextResponse("ok")
