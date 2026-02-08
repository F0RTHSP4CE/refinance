"""API routes for Invoice manipulation"""

from app.dependencies.services import get_invoice_service
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import PaginationSchema
from app.schemas.invoice import (
    FeeInvoiceIssueReportSchema,
    FeeInvoiceIssueSchema,
    InvoiceCreateSchema,
    InvoiceFiltersSchema,
    InvoiceSchema,
    InvoiceUpdateSchema,
)
from app.services.invoice import InvoiceService
from fastapi import APIRouter, Depends

invoice_router = APIRouter(prefix="/invoices", tags=["Invoices"])


@invoice_router.post("", response_model=InvoiceSchema)
def create_invoice(
    invoice: InvoiceCreateSchema,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return invoice_service.create(
        invoice, overrides={"actor_entity_id": actor_entity.id}
    )


@invoice_router.get("/{invoice_id}", response_model=InvoiceSchema)
def read_invoice(
    invoice_id: int,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return invoice_service.get(invoice_id)


@invoice_router.get("", response_model=PaginationSchema[InvoiceSchema])
def read_invoices(
    filters: InvoiceFiltersSchema = Depends(),
    skip: int = 0,
    limit: int = 100,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return invoice_service.get_all(filters, skip, limit)


@invoice_router.patch("/{invoice_id}", response_model=InvoiceSchema)
def update_invoice(
    invoice_id: int,
    invoice_update: InvoiceUpdateSchema,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return invoice_service.update(invoice_id, invoice_update)


@invoice_router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    actor_entity: Entity = Depends(get_entity_from_token),
) -> int:
    return invoice_service.delete(invoice_id)


@invoice_router.post("/issue-fees", response_model=FeeInvoiceIssueReportSchema)
def issue_fee_invoices(
    payload: FeeInvoiceIssueSchema,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return invoice_service.issue_fee_invoices(
        billing_period=payload.billing_period,
        actor_entity_id=actor_entity.id,
    )
