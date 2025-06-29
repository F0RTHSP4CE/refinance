"""Treasury model"""

from app.models.base import BaseModel
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Treasury(BaseModel):
    __tablename__ = "treasuries"

    name: Mapped[str] = mapped_column(String, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship backrefs will be configured on Transaction model
