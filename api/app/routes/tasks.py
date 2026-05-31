"""API routes for manually triggering background tasks."""

from app.dependencies.services import (
    get_stripe_authorization_service,
    get_stripe_deposit_provider_service,
)
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import BaseSchema
from app.services.deposit_providers.stripe import StripeDepositProviderService
from app.services.stripe_authorization import StripeAuthorizationService
from app.tasks.auto_exchange import AutoExchangeTask
from app.tasks.balance_reminder import BalanceReminderTask
from app.tasks.invoice_auto_pay import InvoiceAutoPayTask
from app.tasks.keepz_payments_poll import KeepzPollTask
from fastapi import APIRouter, Depends, Query

tasks_router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskRunResponse(BaseSchema):
    task: str
    result: int
    details: dict | None = None


@tasks_router.post("/auto-exchange/run", response_model=TaskRunResponse)
def run_auto_exchange(_actor: Entity = Depends(get_entity_from_token)):
    return TaskRunResponse(task="auto-exchange", result=AutoExchangeTask().run())


@tasks_router.post("/invoice-auto-pay/run", response_model=TaskRunResponse)
def run_invoice_auto_pay(_actor: Entity = Depends(get_entity_from_token)):
    return TaskRunResponse(task="invoice-auto-pay", result=InvoiceAutoPayTask().run())


@tasks_router.post("/keepz-poll/run", response_model=TaskRunResponse)
def run_keepz_poll(_actor: Entity = Depends(get_entity_from_token)):
    return TaskRunResponse(task="keepz-poll", result=KeepzPollTask().run())


@tasks_router.post("/stripe-poll/run", response_model=TaskRunResponse)
def run_stripe_poll(
    _actor: Entity = Depends(get_entity_from_token),
    stripe_deposit_provider_service: StripeDepositProviderService = Depends(
        get_stripe_deposit_provider_service
    ),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
):
    n = stripe_deposit_provider_service.poll_pending_deposits()
    n += stripe_authorization_service.poll_subscription_invoice_deposits()
    return TaskRunResponse(task="stripe-poll", result=n)


@tasks_router.post("/stripe-entity-charge/run", response_model=TaskRunResponse)
def run_stripe_entity_charge(
    dry_run: bool = Query(default=False),
    _actor: Entity = Depends(get_entity_from_token),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
):
    if dry_run:
        plans = stripe_authorization_service.preview_weekly_entity_dynamic_charges()
        return TaskRunResponse(
            task="stripe-entity-charge",
            result=sum(1 for plan in plans if plan.get("will_charge")),
            details={"dry_run": True, "plans": plans},
        )

    return TaskRunResponse(
        task="stripe-entity-charge",
        result=stripe_authorization_service.run_weekly_entity_dynamic_charges(),
    )


@tasks_router.get("/stripe-entity-charge/debug", response_model=dict)
def debug_stripe_entity_charge(
    entity_id: int = Query(),
    _actor: Entity = Depends(get_entity_from_token),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
):
    return stripe_authorization_service.debug_entity_dynamic_charge(entity_id)


@tasks_router.post("/balance-reminder/run", response_model=TaskRunResponse)
def run_balance_reminder(_actor: Entity = Depends(get_entity_from_token)):
    return TaskRunResponse(task="balance-reminder", result=BalanceReminderTask().run())
