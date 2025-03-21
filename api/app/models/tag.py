"""Tag model"""

from app.models.base import BaseModel
from sqlalchemy.orm import Mapped, mapped_column


class Tag(BaseModel):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(unique=True)


# this list is used by db.py to create system tags
TAG_BOOTSTRAP: list[Tag] = [
    Tag(id=1, name="sys", comment="things defined in refinance code logic"),
    Tag(id=2, name="resident", comment="hackerspace residents"),
    Tag(id=3, name="fee", comment="monthly resident's fee"),
]
