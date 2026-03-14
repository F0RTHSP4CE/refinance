"""API routes for sending notifications"""

from app.dependencies.services import (
    get_entity_service,
    get_notification_service,
)
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import BaseSchema
from app.services.entity import EntityService
from app.services.notification import NotificationService
from fastapi import APIRouter, Depends
from pydantic import BaseModel

notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationSendRequest(BaseModel):
    entity_id: int
    message: str


class NotificationSendResponse(BaseSchema):
    entity_id: int
    results: dict[str, bool]


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
