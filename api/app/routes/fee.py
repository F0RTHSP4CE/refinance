"""Fee routes"""

from app.dependencies.services import get_fee_allocation_service, get_fee_service
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.fee import (
    FeeAllocationSelectionSchema,
    FeeAmountSchema,
    FeeConfigSchema,
    FeeDirectedAllocationUpdateSchema,
    FeeFiltersSchema,
    FeeInvoiceBulkCreateReportSchema,
    FeeInvoiceBulkCreateSchema,
    FeeInvoiceSettlementCreateSchema,
    FeePolicyOverrideSchema,
    FeePolicyOverrideUpdateSchema,
    FeeSchema,
)
from app.schemas.transaction import TransactionSchema
from app.services.fee import FeeService
from app.services.fee_allocation import FeeAllocationService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/fees", tags=["Fees"])


@router.get("/", response_model=list[FeeSchema])
def get_fees(
    filters: FeeFiltersSchema = Depends(),
    service: FeeService = Depends(get_fee_service),
):
    return service.get_fees(filters)


@router.get("/amounts", response_model=list[FeeAmountSchema])
def get_fee_config(
    service: FeeService = Depends(get_fee_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.get_fee_amounts()


@router.get("/config", response_model=FeeConfigSchema)
def get_directed_fee_config(
    service: FeeAllocationService = Depends(get_fee_allocation_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.get_config()


@router.post("/invoices/bulk", response_model=FeeInvoiceBulkCreateReportSchema)
def bulk_create_fee_invoices(
    payload: FeeInvoiceBulkCreateSchema,
    service: FeeAllocationService = Depends(get_fee_allocation_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.create_fee_invoices(payload, actor_entity)


@router.get(
    "/invoices/{invoice_id}/directed-allocation",
    response_model=FeeAllocationSelectionSchema,
)
def get_directed_allocation(
    invoice_id: int,
    service: FeeAllocationService = Depends(get_fee_allocation_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.get_selection(invoice_id, actor_entity)


@router.patch(
    "/invoices/{invoice_id}/directed-allocation",
    response_model=FeeAllocationSelectionSchema,
)
def update_directed_allocation(
    invoice_id: int,
    payload: FeeDirectedAllocationUpdateSchema,
    service: FeeAllocationService = Depends(get_fee_allocation_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.update_directed_allocation(invoice_id, payload, actor_entity)


@router.post(
    "/invoices/{invoice_id}/settlement",
    response_model=list[TransactionSchema],
)
def settle_fee_invoice(
    invoice_id: int,
    payload: FeeInvoiceSettlementCreateSchema,
    service: FeeAllocationService = Depends(get_fee_allocation_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.settle_fee_invoice(
        invoice_id,
        payload.currency,
        actor_entity,
        status=payload.status,
    )


@router.get("/policies/{entity_id}", response_model=FeePolicyOverrideSchema | None)
def get_fee_policy(
    entity_id: int,
    service: FeeAllocationService = Depends(get_fee_allocation_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.get_policy(entity_id, actor_entity)


@router.put("/policies/{entity_id}", response_model=FeePolicyOverrideSchema)
def upsert_fee_policy(
    entity_id: int,
    payload: FeePolicyOverrideUpdateSchema,
    service: FeeAllocationService = Depends(get_fee_allocation_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.upsert_policy(entity_id, payload, actor_entity)


@router.delete("/policies/{entity_id}")
def delete_fee_policy(
    entity_id: int,
    service: FeeAllocationService = Depends(get_fee_allocation_service),
    actor_entity: Entity = Depends(get_entity_from_token),
) -> int:
    return service.delete_policy(entity_id, actor_entity)
