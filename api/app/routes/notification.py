"""API routes for sending notifications"""

from app.dependencies.services import (
    get_balance_service,
    get_entity_service,
    get_notification_service,
)
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import BaseSchema
from app.services.balance import BalanceService
from app.services.entity import EntityService
from app.services.notification import NotificationService
from app.tasks.balance_reminder import send_balance_reminder, send_reminders_to_all
from app.uow import get_uow
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationSendRequest(BaseModel):
    entity_id: int
    message: str


class NotificationSendResponse(BaseSchema):
    entity_id: int
    results: dict[str, bool]


class BalanceReminderResponse(BaseSchema):
    entity_id: int
    sent: bool
    results: dict[str, bool]


class BalanceReminderAllResponse(BaseSchema):
    total_sent: int


@notification_router.post("/send", response_model=NotificationSendResponse)
def send_notification(
    request: NotificationSendRequest,
    entity_service: EntityService = Depends(get_entity_service),
    notification_service: NotificationService = Depends(get_notification_service),
    _actor: Entity = Depends(get_entity_from_token),
):
    entity = entity_service.get(request.entity_id)
    results = notification_service.send(entity, request.message)
    return NotificationSendResponse(entity_id=entity.id, results=results)


@notification_router.post(
    "/balance-reminder/{entity_id}", response_model=BalanceReminderResponse
)
def send_balance_reminder_for_entity(
    entity_id: int,
    db: Session = Depends(get_uow),
    entity_service: EntityService = Depends(get_entity_service),
    balance_service: BalanceService = Depends(get_balance_service),
    notification_service: NotificationService = Depends(get_notification_service),
    _actor: Entity = Depends(get_entity_from_token),
):
    entity = entity_service.get(entity_id)
    results = send_balance_reminder(
        entity,
        db=db,
        balance_service=balance_service,
        notification_service=notification_service,
    )
    results = results or {}
    return BalanceReminderResponse(
        entity_id=entity_id,
        sent=any(results.values()),
        results=results,
    )


@notification_router.post(
    "/balance-reminder", response_model=BalanceReminderAllResponse
)
def send_balance_reminders_all(
    db: Session = Depends(get_uow),
    balance_service: BalanceService = Depends(get_balance_service),
    notification_service: NotificationService = Depends(get_notification_service),
    _actor: Entity = Depends(get_entity_from_token),
):
    total_sent = send_reminders_to_all(db, balance_service, notification_service)
    return BalanceReminderAllResponse(total_sent=total_sent)
