"""Base for all ORM models"""

from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    # do not create separate table for this class
    __abstract__ = True

    # everything should have an id and a comment
    id: Mapped[int] = mapped_column(primary_key=True)
    comment: Mapped[Optional[str]]
