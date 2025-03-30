"""API routes for deposit providers"""

from typing import Annotated

from app.errors.common import NotFoundError
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.deposit_providers.cryptapi import (
    CryptAPICallbackSchema,
    CryptAPIDepositCreateSchema,
)
from app.services.deposit_providers.cryptapi import CryptAPIDepositProviderService
from fastapi import APIRouter, Depends, Path, Query

deposits_router = APIRouter(prefix="/deposits", tags=["DepositProviders"])


@deposits_router.post("/providers/cryptapi")
def cryptapi_create_deposit(
    schema: CryptAPIDepositCreateSchema = Depends(),
    cryptapi_deposit_provider_service: CryptAPIDepositProviderService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return cryptapi_deposit_provider_service.create_deposit(schema, actor_entity)
