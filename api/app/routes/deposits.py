"""API routes for deposit providers"""

from typing import Annotated

from app.dependencies.services import (
    get_cryptapi_deposit_provider_service,
    get_deposit_service,
    get_keepz_deposit_provider_service,
    get_stripe_authorization_service,
    get_stripe_deposit_provider_service,
)
from app.errors.common import NotFoundError
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import PaginationSchema
from app.schemas.deposit import DepositFiltersSchema, DepositSchema
from app.schemas.deposit_providers.cryptapi import (
    CryptAPICallbackSchema,
    CryptAPIDepositCreateSchema,
)
from app.schemas.deposit_providers.keepz import KeepzDepositCreateSchema
from app.schemas.deposit_providers.stripe import StripeDepositCreateSchema
from app.schemas.stripe_authorization import (
    StripeAuthorizationListSchema,
    StripeAuthorizationPrioritySchema,
    StripeAuthorizationSchema,
    StripeAuthorizationSessionSchema,
    StripeAuthorizationSetupSchema,
)
from app.services.deposit import DepositService
from app.services.deposit_providers.cryptapi import CryptAPIDepositProviderService
from app.services.deposit_providers.keepz import KeepzDepositProviderService
from app.services.deposit_providers.stripe import StripeDepositProviderService
from app.services.stripe_authorization import StripeAuthorizationService
from fastapi import APIRouter, Depends, Path, Query

deposits_router = APIRouter(prefix="/deposits", tags=["DepositProviders"])


@deposits_router.get("", response_model=PaginationSchema[DepositSchema])
def read_deposits(
    filters: DepositFiltersSchema = Depends(),
    skip: int = 0,
    limit: int = 100,
    deposit_service: DepositService = Depends(get_deposit_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return deposit_service.get_all(filters, skip, limit)


@deposits_router.get("/{deposit_id}", response_model=DepositSchema)
def read_deposit(
    deposit_id: int,
    deposit_service: DepositService = Depends(get_deposit_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return deposit_service.get(deposit_id)


@deposits_router.post("/providers/cryptapi", response_model=DepositSchema)
def cryptapi_create_deposit(
    schema: CryptAPIDepositCreateSchema = Depends(),
    cryptapi_deposit_provider_service: CryptAPIDepositProviderService = Depends(
        get_cryptapi_deposit_provider_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return cryptapi_deposit_provider_service.create_deposit(schema, actor_entity)


@deposits_router.post("/providers/keepz", response_model=DepositSchema)
def keepz_create_deposit(
    schema: KeepzDepositCreateSchema = Depends(),
    keepz_deposit_provider_service: KeepzDepositProviderService = Depends(
        get_keepz_deposit_provider_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return keepz_deposit_provider_service.create_deposit(schema, actor_entity)


@deposits_router.post("/providers/stripe", response_model=DepositSchema)
def stripe_create_deposit(
    schema: StripeDepositCreateSchema = Depends(),
    stripe_deposit_provider_service: StripeDepositProviderService = Depends(
        get_stripe_deposit_provider_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return stripe_deposit_provider_service.create_deposit(schema, actor_entity)


@deposits_router.post(
    "/providers/stripe/authorizations/setup-session",
    response_model=StripeAuthorizationSessionSchema,
)
def stripe_create_authorization_setup_session(
    schema: StripeAuthorizationSetupSchema = Depends(),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    session_id, session_url = stripe_authorization_service.create_setup_session(
        schema,
        actor_entity,
    )
    return StripeAuthorizationSessionSchema(
        checkout_session_id=session_id,
        checkout_session_url=session_url,
    )


@deposits_router.post(
    "/providers/stripe/authorizations/sync-session",
    response_model=StripeAuthorizationSchema | None,
)
def stripe_sync_authorization_session(
    checkout_session_id: str = Query(),
    entity_id: int | None = Query(default=None),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return stripe_authorization_service.sync_setup_session(
        checkout_session_id=checkout_session_id,
        actor_entity=actor_entity,
        fallback_entity_id=entity_id or actor_entity.id,
    )


@deposits_router.get(
    "/providers/stripe/authorizations",
    response_model=StripeAuthorizationListSchema,
)
def stripe_list_authorizations(
    entity_id: int | None = Query(default=None),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    target_entity_id = entity_id or actor_entity.id
    authorizations = stripe_authorization_service.list_for_entity(target_entity_id)
    return StripeAuthorizationListSchema(items=authorizations)


@deposits_router.post(
    "/providers/stripe/authorizations/{authorization_id}/enable",
    response_model=StripeAuthorizationSchema,
)
def stripe_enable_authorization(
    authorization_id: int,
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return stripe_authorization_service.set_active(
        authorization_id=authorization_id,
        actor_entity=actor_entity,
        active=True,
    )


@deposits_router.post(
    "/providers/stripe/authorizations/{authorization_id}/disable",
    response_model=StripeAuthorizationSchema,
)
def stripe_disable_authorization(
    authorization_id: int,
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return stripe_authorization_service.set_active(
        authorization_id=authorization_id,
        actor_entity=actor_entity,
        active=False,
    )


@deposits_router.post(
    "/providers/stripe/authorizations/{authorization_id}/priority",
    response_model=StripeAuthorizationSchema,
)
def stripe_set_authorization_priority(
    authorization_id: int,
    schema: StripeAuthorizationPrioritySchema = Depends(),
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return stripe_authorization_service.set_priority(
        authorization_id=authorization_id,
        actor_entity=actor_entity,
        priority=schema.priority,
    )


@deposits_router.delete(
    "/providers/stripe/authorizations/{authorization_id}",
    response_model=dict,
)
def stripe_delete_authorization(
    authorization_id: int,
    stripe_authorization_service: StripeAuthorizationService = Depends(
        get_stripe_authorization_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    deleted_id = stripe_authorization_service.delete(authorization_id, actor_entity)
    return {"id": deleted_id, "deleted": True}
