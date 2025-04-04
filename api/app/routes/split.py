"""API routes for Split manipulation"""

from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import PaginationSchema
from app.schemas.split import (
    SplitCreateSchema,
    SplitFiltersSchema,
    SplitParticipantAddSchema,
    SplitSchema,
    SplitUpdateSchema,
)
from app.schemas.tag import TagSchema
from app.services.split import SplitService
from fastapi import APIRouter, Depends

split_router = APIRouter(prefix="/splits", tags=["Splits"])


@split_router.post("", response_model=SplitSchema)
def create_split(
    split: SplitCreateSchema,
    split_service: SplitService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return SplitSchema.model_validate(
        split_service.create(split, overrides={"actor_entity_id": actor_entity.id})
    )


@split_router.get("/{split_id}", response_model=SplitSchema)
def read_split(
    split_id: int,
    split_service: SplitService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return SplitSchema.model_validate(split_service.get(split_id))


@split_router.get("", response_model=PaginationSchema[SplitSchema])
def read_splits(
    filters: SplitFiltersSchema = Depends(),
    skip: int = 0,
    limit: int = 100,
    split_service: SplitService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return PaginationSchema.model_validate(split_service.get_all(filters, skip, limit))


@split_router.patch("/{split_id}", response_model=SplitSchema)
def update_split(
    split_id: int,
    split_update: SplitUpdateSchema,
    split_service: SplitService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return SplitSchema.model_validate(split_service.update(split_id, split_update))


@split_router.delete("/{split_id}")
def delete_split(
    split_id: int,
    split_service: SplitService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
) -> int:
    return split_service.delete(split_id)


@split_router.post("/{split_id}/perform", response_model=SplitSchema)
def perform_split(
    split_id: int,
    split_service: SplitService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return SplitSchema.model_validate(
        split_service.perform(split_id, actor_entity=actor_entity)
    )


@split_router.post("/{split_id}/tags", response_model=TagSchema)
def add_tag_to_split(
    split_id: int,
    tag_id: int,
    split_service: SplitService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return TagSchema.model_validate(split_service.add_tag(split_id, tag_id))


@split_router.delete("/{split_id}/tags", response_model=TagSchema)
def remove_tag_from_split(
    split_id: int,
    tag_id: int,
    split_service: SplitService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return TagSchema.model_validate(split_service.remove_tag(split_id, tag_id))


@split_router.post("/{split_id}/participants", response_model=SplitSchema)
def add_participant_to_split(
    split_id: int,
    participant_add_schema: SplitParticipantAddSchema,
    split_service: SplitService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return SplitSchema.model_validate(
        split_service.add_participant(split_id, participant_add_schema)
    )


@split_router.delete("/{split_id}/participants", response_model=SplitSchema)
def remove_participant_from_split(
    split_id: int,
    entity_id: int,
    split_service: SplitService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return SplitSchema.model_validate(
        split_service.remove_participant(split_id, entity_id)
    )
