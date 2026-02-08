"""API routes for Entity manipulation"""

from app.dependencies.services import get_entity_service
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import PaginationSchema
from app.schemas.entity import (
    EntityCreateSchema,
    EntityFiltersSchema,
    EntitySchema,
    EntityUpdateSchema,
)
from app.schemas.entity_card import EntityCardCreateSchema, EntityCardReadSchema
from app.services.entity import EntityService
from fastapi import APIRouter, Depends

entity_router = APIRouter(prefix="/entities", tags=["Entities"])


@entity_router.post("", response_model=EntitySchema)
def create_entity(
    entity: EntityCreateSchema,
    entity_service: EntityService = Depends(get_entity_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.create(entity)


@entity_router.get("/me", response_model=EntitySchema)
def read_me(
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return actor_entity


@entity_router.get("/{entity_id}", response_model=EntitySchema)
def read_entity(
    entity_id: int,
    entity_service: EntityService = Depends(get_entity_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.get(entity_id)


@entity_router.get("", response_model=PaginationSchema[EntitySchema])
def read_entities(
    filters: EntityFiltersSchema = Depends(),
    skip: int = 0,
    limit: int = 100,
    entity_service: EntityService = Depends(get_entity_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.get_all(filters, skip, limit)


@entity_router.patch("/{entity_id}", response_model=EntitySchema)
def update_entity(
    entity_id: int,
    entity_update: EntityUpdateSchema,
    entity_service: EntityService = Depends(get_entity_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.update(entity_id, entity_update)


# ---- Cards management -----------------------------------------------------


@entity_router.get("/{entity_id}/cards", response_model=list[EntityCardReadSchema])
def list_entity_cards(
    entity_id: int,
    entity_service: EntityService = Depends(get_entity_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.list_cards(entity_id)


@entity_router.post("/{entity_id}/cards", response_model=EntityCardReadSchema)
def add_entity_card(
    entity_id: int,
    payload: EntityCardCreateSchema,
    entity_service: EntityService = Depends(get_entity_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    card = entity_service.add_card(
        entity_id, card_hash=payload.card_hash, comment=payload.comment
    )
    return card


@entity_router.delete("/{entity_id}/cards/{card_id}")
def remove_entity_card(
    entity_id: int,
    card_id: int,
    entity_service: EntityService = Depends(get_entity_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.remove_card(entity_id, card_id)
