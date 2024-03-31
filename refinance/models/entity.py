"""Basic unit of refinance system. May receive or send money."""

from sqlalchemy.orm import Mapped, mapped_column

from refinance.models.base import BaseModel


class Entity(BaseModel):
    __tablename__ = "entities"

    name: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)
