"""API routes for Keepz authentication."""

from app.dependencies.services import get_keepz_service
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.keepz import (
    KeepzAuthStatusSchema,
    KeepzLoginSchema,
    KeepzSendSmsSchema,
)
from app.services.keepz import KeepzService
from fastapi import APIRouter, Depends

keepz_router = APIRouter(prefix="/keepz", tags=["Keepz"])


@keepz_router.get("/auth/status", response_model=KeepzAuthStatusSchema)
def keepz_auth_status(
    keepz_service: KeepzService = Depends(get_keepz_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return keepz_service.auth_status()


@keepz_router.post("/auth/send-sms")
def keepz_send_sms(
    request: KeepzSendSmsSchema,
    keepz_service: KeepzService = Depends(get_keepz_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    keepz_service.send_sms(phone=request.phone, country_code=request.country_code)
    return {"sent": True}


@keepz_router.post("/auth/login", response_model=KeepzAuthStatusSchema)
def keepz_login(
    request: KeepzLoginSchema,
    keepz_service: KeepzService = Depends(get_keepz_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return keepz_service.login_with_sms(
        phone=request.phone,
        country_code=request.country_code,
        code=request.code,
        user_type=request.user_type,
        device_token=request.device_token,
        mobile_name=request.mobile_name,
        mobile_os=request.mobile_os,
    )
