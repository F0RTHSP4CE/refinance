"""Public guest donation endpoints — no authentication required."""

from uuid import UUID

from app.dependencies.services import (
    get_deposit_service,
    get_keepz_deposit_provider_service,
    get_stripe_authorization_service,
)
from app.errors.common import NotFoundError
from app.schemas.deposit import DepositUpdateSchema
from app.schemas.deposit_providers.keepz import KeepzDepositCreateSchema
from app.schemas.donation import (
    DonationCreateSchema,
    DonationPortalResponseSchema,
    DonationResponseSchema,
    DonationSubscribeResponseSchema,
    DonationSubscribeSchema,
    get_validated_donation,
    get_validated_subscribe,
)
from app.schemas.stripe_authorization import StripeAuthorizationSetupSchema
from app.seeding import anonymous_entity, donation_tag
from app.services.deposit import DepositService
from app.services.deposit_providers.keepz import KeepzDepositProviderService
from app.services.stripe_authorization import StripeAuthorizationService
from fastapi import APIRouter, Depends, HTTPException, Query

donation_router = APIRouter(prefix="/donations", tags=["Donations"])


def _payment_url(deposit) -> str | None:
    if not deposit.details:
        return None
    return (deposit.details.get("keepz") or {}).get("payment_url")


@donation_router.post("", response_model=DonationResponseSchema)
def create_donation(
    schema: DonationCreateSchema = Depends(get_validated_donation),
    keepz_provider: KeepzDepositProviderService = Depends(
        get_keepz_deposit_provider_service
    ),
):
    keepz_schema = KeepzDepositCreateSchema(
        to_entity_id=anonymous_entity.id,
        amount=schema.amount,
        currency=schema.currency,
    )
    deposit = keepz_provider.create_deposit(keepz_schema, actor_entity=anonymous_entity)

    # Store donation comment and tag the deposit in one update call
    details = dict(deposit.details or {})
    if schema.comment:
        details["donation_comment"] = schema.comment
    keepz_provider.deposit_service.update(
        deposit.id,
        DepositUpdateSchema(details=details, tag_ids=[donation_tag.id]),
    )
    deposit = keepz_provider.deposit_service.get(deposit.id)

    return DonationResponseSchema(
        deposit_uuid=deposit.uuid,
        status=deposit.status,
        payment_url=_payment_url(deposit),
        amount=str(deposit.amount),
        currency=deposit.currency.upper(),
    )


@donation_router.get("/{deposit_uuid}", response_model=DonationResponseSchema)
def get_donation(
    deposit_uuid: UUID,
    deposit_service: DepositService = Depends(get_deposit_service),
):
    try:
        deposit = deposit_service.get_by_uuid(deposit_uuid)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Donation not found")

    # Only expose deposits targeting the anonymous entity
    if deposit.to_entity_id != anonymous_entity.id:
        raise HTTPException(status_code=404, detail="Donation not found")

    return DonationResponseSchema(
        deposit_uuid=deposit.uuid,
        status=deposit.status,
        payment_url=_payment_url(deposit),
        amount=str(deposit.amount),
        currency=deposit.currency.upper(),
    )


@donation_router.post("/subscribe", response_model=DonationSubscribeResponseSchema)
def create_subscription_donation(
    schema: DonationSubscribeSchema = Depends(get_validated_subscribe),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
):
    setup_schema = StripeAuthorizationSetupSchema(
        entity_id=anonymous_entity.id,
        mode="guest_static",
        static_amount=schema.amount,
        static_currency=schema.currency,
        success_url=schema.success_url,
        cancel_url=schema.cancel_url,
        donation_comment=schema.comment or None,
    )
    _session_id, session_url = stripe_authorization_service.create_setup_session(
        setup_schema, anonymous_entity
    )
    if not session_url:
        raise HTTPException(
            status_code=502, detail="Stripe did not return a checkout URL"
        )
    return DonationSubscribeResponseSchema(checkout_session_url=session_url)


@donation_router.post("/subscribe/sync", response_model=None)
def sync_subscription_donation(
    checkout_session_id: str = Query(),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
):
    auth = stripe_authorization_service.sync_setup_session(
        checkout_session_id=checkout_session_id,
        actor_entity=anonymous_entity,
        fallback_entity_id=anonymous_entity.id,
    )
    try:
        stripe_authorization_service.charge_new_guest_static(auth)
    except Exception:
        pass  # charge failure doesn't cancel the subscription
    return {"ok": True}


@donation_router.get("/portal", response_model=DonationPortalResponseSchema)
def get_donation_portal(
    checkout_session_id: str = Query(),
    return_url: str = Query(),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
):
    portal_url = stripe_authorization_service.get_customer_portal_url(
        checkout_session_id=checkout_session_id,
        return_url=return_url,
    )
    return DonationPortalResponseSchema(portal_url=portal_url)
