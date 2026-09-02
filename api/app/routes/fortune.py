"""Authenticated Fortune lottery endpoints."""

from app.dependencies.services import get_fortune_service
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.fortune import FortuneGameSchema, FortunePlaySchema
from app.services.fortune import FortuneService
from fastapi import APIRouter, Depends

fortune_router = APIRouter(prefix="/fortune/games", tags=["Fortune"])


@fortune_router.post(
    "", response_model=FortuneGameSchema, response_model_exclude_none=True
)
def create_fortune_game(
    fortune_service: FortuneService = Depends(get_fortune_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return fortune_service.create_game(actor_entity)


@fortune_router.get(
    "/{game_id}", response_model=FortuneGameSchema, response_model_exclude_none=True
)
def read_fortune_game(
    game_id: int,
    fortune_service: FortuneService = Depends(get_fortune_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return fortune_service.get_game(game_id, actor_entity)


@fortune_router.post(
    "/{game_id}/play",
    response_model=FortuneGameSchema,
    response_model_exclude_none=True,
)
def play_fortune_game(
    game_id: int,
    play: FortunePlaySchema,
    fortune_service: FortuneService = Depends(get_fortune_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return fortune_service.play_game(game_id, play, actor_entity)
