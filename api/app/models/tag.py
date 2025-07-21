"""Tag model"""

from app.models.base import BaseModel
from sqlalchemy.orm import Mapped, mapped_column


class Tag(BaseModel):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(unique=True)
