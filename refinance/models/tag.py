from sqlalchemy.orm import Mapped, mapped_column

from refinance.models.base import BaseModel


class Tag(BaseModel):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column()
