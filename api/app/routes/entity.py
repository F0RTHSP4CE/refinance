"""API routes for Entity manipulation"""

from fastapi import APIRouter, Depends

from app.errors.entity import EntitiesAlreadyPresent
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import PaginationSchema
from app.schemas.entity import (
    EntityCreateSchema,
    EntityFiltersSchema,
    EntitySchema,
    EntityUpdateSchema,
)
from app.schemas.tag import TagSchema
from app.services.entity import EntityService

entity_router = APIRouter(prefix="/entities", tags=["Entities"])


@entity_router.post("/first", response_model=EntitySchema)
def create_first_entity(
    entity: EntityCreateSchema,
    entity_service: EntityService = Depends(),
):
    """
    Create very first Entity.
    Does NOT require authentication (X-Token Header).

    Useful for creating first account after deploying an application
    """
    if entity_service.get_all().total == 0:
        return entity_service.create(entity)
    else:
        raise EntitiesAlreadyPresent


@entity_router.post("", response_model=EntitySchema)
def create_entity(
    entity: EntityCreateSchema,
    entity_service: EntityService = Depends(),
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
    entity_service: EntityService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.get(entity_id)


@entity_router.get("/telegram_id/{telegram_id}", response_model=EntitySchema)
def get_entity_by_telegram_id(
    telegram_id: int,
    entity_service: EntityService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.get_by_telegram_id(telegram_id)


@entity_router.get("", response_model=PaginationSchema[EntitySchema])
def read_entities(
    filters: EntityFiltersSchema = Depends(),
    skip: int = 0,
    limit: int = 100,
    entity_service: EntityService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.get_all(filters, skip, limit)


@entity_router.patch("/{entity_id}", response_model=EntitySchema)
def update_entity(
    entity_id: int,
    entity_update: EntityUpdateSchema,
    entity_service: EntityService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.update(entity_id, entity_update)


@entity_router.post("/{entity_id}/tags", response_model=TagSchema)
def add_tag_to_entity(
    entity_id: int,
    tag_id: int,
    entity_service: EntityService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.add_tag(entity_id, tag_id)


@entity_router.delete("/{entity_id}/tags", response_model=TagSchema)
def remove_tag_from_entity(
    entity_id: int,
    tag_id: int,
    entity_service: EntityService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return entity_service.remove_tag(entity_id, tag_id)
