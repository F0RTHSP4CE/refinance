"""API routes for Entity manipulation"""

from fastapi import APIRouter, Depends

from refinance.schemas.base import PaginationSchema
from refinance.schemas.entity import EntityCreateSchema, EntityFiltersSchema, EntitySchema, EntityUpdateSchema
from refinance.services.entity import EntityService

entity_router = APIRouter(prefix="/entities", tags=["Entities"])


@entity_router.post("/", response_model=EntitySchema)
def create_entity(
    entity: EntityCreateSchema,
    entity_service: EntityService = Depends(),
) -> EntitySchema:
    return entity_service.create(entity)


@entity_router.get("/{entity_id}", response_model=EntitySchema)
def read_entity(
    entity_id: int,
    entity_service: EntityService = Depends(),
) -> EntitySchema:
    return entity_service.get(entity_id)


@entity_router.get("/", response_model=PaginationSchema[EntitySchema])
def read_entities(
    filters: EntityFiltersSchema = Depends(),
    skip: int = 0,
    limit: int = 100,
    entity_service: EntityService = Depends(),
) -> PaginationSchema[EntitySchema]:
    return entity_service.get_all(filters, skip, limit)


@entity_router.patch("/{entity_id}", response_model=EntitySchema)
def update_entity(
    entity_id: int,
    entity_update: EntityUpdateSchema,
    entity_service: EntityService = Depends(),
) -> EntitySchema:
    return entity_service.update(entity_id, entity_update)
