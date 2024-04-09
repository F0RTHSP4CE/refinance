"""Main unit of refinance system. May receive or send money."""

from typing import List

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from refinance.models.base import BaseModel
from refinance.models.tag import Tag

entities_tags = Table(
    "entities_tags",
    BaseModel.metadata,
    Column("entity_id", ForeignKey("entities.id")),
    Column("tag_id", ForeignKey("tags.id")),
)


class Entity(BaseModel):
    __tablename__ = "entities"

    name: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)
    tags: Mapped[List[Tag]] = relationship(secondary=entities_tags)
