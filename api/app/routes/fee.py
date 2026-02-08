"""Fee routes"""

from app.dependencies.services import get_fee_service
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.fee import (
    FeeAmountSchema,
    FeeFiltersSchema,
    FeeInvoiceIssueReportSchema,
    FeeInvoiceIssueSchema,
    FeeSchema,
)
from app.services.fee import FeeService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/fees", tags=["Fees"])


@router.get("/", response_model=list[FeeSchema])
def get_fees(
    filters: FeeFiltersSchema = Depends(),
    service: FeeService = Depends(get_fee_service),
):
    return service.get_fees(filters)


@router.get("/config", response_model=list[FeeAmountSchema])
def get_fee_config(
    service: FeeService = Depends(get_fee_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.get_fee_amounts()


@router.post("/issue-invoices", response_model=FeeInvoiceIssueReportSchema)
def issue_fee_invoices(
    payload: FeeInvoiceIssueSchema,
    service: FeeService = Depends(get_fee_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.issue_fee_invoices(
        billing_period=payload.billing_period,
        actor_entity_id=actor_entity.id,
    )
