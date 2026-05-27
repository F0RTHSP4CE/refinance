"""API routes for manually triggering background tasks."""

from app.dependencies.services import get_stripe_deposit_provider_service
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import BaseSchema
from app.services.deposit_providers.stripe import StripeDepositProviderService
from app.tasks.auto_exchange import AutoExchangeTask
from app.tasks.balance_reminder import BalanceReminderTask
from app.tasks.invoice_auto_pay import InvoiceAutoPayTask
from app.tasks.keepz_payments_poll import KeepzPollTask
from fastapi import APIRouter, Depends

tasks_router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskRunResponse(BaseSchema):
    task: str
    result: int


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
):
    return TaskRunResponse(
        task="stripe-poll",
        result=stripe_deposit_provider_service.poll_pending_deposits(),
    )


@tasks_router.post("/balance-reminder/run", response_model=TaskRunResponse)
def run_balance_reminder(_actor: Entity = Depends(get_entity_from_token)):
    return TaskRunResponse(task="balance-reminder", result=BalanceReminderTask().run())
