"""Treasury model"""

from typing import TYPE_CHECKING

from app.models.base import BaseModel
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.entity import Entity


class Treasury(BaseModel):
    __tablename__ = "treasuries"

    name: Mapped[str] = mapped_column(String, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    author_entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("entities.id"), nullable=True
    )
    author_entity: Mapped["Entity | None"] = relationship(
        foreign_keys=[author_entity_id]
    )

    # Relationship backrefs will be configured on Transaction model
