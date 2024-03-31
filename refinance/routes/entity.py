"""API routes for Entity manipulation"""

from fastapi import APIRouter, Depends

from refinance.schemas.entity import (
    EntityCreateSchema,
    EntitySchema,
    EntityUpdateSchema,
)
from refinance.services.entity import EntityService

entity_router = APIRouter(prefix="/entities", tags=["Entities"])


@entity_router.post("/", response_model=EntitySchema)
def create_entity(
    entity: EntityCreateSchema,
    entity_service: EntityService = Depends(),
):
    return entity_service.create(entity)


@entity_router.get("/{entity_id}", response_model=EntitySchema)
def read_entity(
    entity_id: int,
    entity_service: EntityService = Depends(),
):
    return entity_service.get(entity_id)


@entity_router.get("/", response_model=list[EntitySchema])
def read_entities(
    skip: int = 0,
    limit: int = 10,
    entity_service: EntityService = Depends(),
):
    return entity_service.get_all(skip=skip, limit=limit)


@entity_router.patch("/{entity_id}", response_model=EntitySchema)
def update_entity(
    entity_id: int,
    entity_update: EntityUpdateSchema,
    entity_service: EntityService = Depends(),
):
    return entity_service.update(entity_id, entity_update)
