"""Public guest donation endpoints — no authentication required."""

from uuid import UUID

from app.dependencies.services import (
    get_deposit_service,
    get_keepz_deposit_provider_service,
)
from app.errors.common import NotFoundError
from app.schemas.deposit import DepositUpdateSchema
from app.schemas.deposit_providers.keepz import KeepzDepositCreateSchema
from app.schemas.donation import (
    DonationCreateSchema,
    DonationResponseSchema,
    get_validated_donation,
)
from app.seeding import anonymous_entity, donation_tag
from app.services.deposit import DepositService
from app.services.deposit_providers.keepz import KeepzDepositProviderService
from fastapi import APIRouter, Depends, HTTPException

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
