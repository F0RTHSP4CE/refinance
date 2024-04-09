"""API routes for Tag manipulation"""

from fastapi import APIRouter, Depends

from refinance.schemas.base import PaginationSchema
from refinance.schemas.tag import (
    TagCreateSchema,
    TagFiltersSchema,
    TagSchema,
    TagUpdateSchema,
)
from refinance.services.tag import TagService

tag_router = APIRouter(prefix="/tags", tags=["Tags"])


@tag_router.post("/", response_model=TagSchema)
def create_tag(
    tag: TagCreateSchema,
    tag_service: TagService = Depends(),
):
    return tag_service.create(tag)


@tag_router.get("/{tag_id}", response_model=TagSchema)
def read_tag(
    tag_id: int,
    tag_service: TagService = Depends(),
):
    return tag_service.get(tag_id)


@tag_router.get("/", response_model=PaginationSchema[TagSchema])
def read_tags(
    filters: TagFiltersSchema = Depends(),
    skip: int = 0,
    limit: int = 100,
    tag_service: TagService = Depends(),
):
    return tag_service.get_all(filters, skip, limit)


@tag_router.patch("/{tag_id}", response_model=TagSchema)
def update_tag(
    tag_id: int,
    tag_update: TagUpdateSchema,
    tag_service: TagService = Depends(),
):
    return tag_service.update(tag_id, tag_update)


@tag_router.delete("/{tag_id}")
def delete_tag(tag_id: int, tag_service: TagService = Depends()) -> int:
    return tag_service.delete(tag_id)
