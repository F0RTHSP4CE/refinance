"""EntityCard model to manage physical/payment cards for entities."""

from app.models.base import BaseModel
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class EntityCard(BaseModel):
    __tablename__ = "entity_cards"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    card_hash: Mapped[str] = mapped_column(index=True, nullable=False, unique=True)

    entity = relationship("Entity", back_populates="cards")
