"""Tag service"""

from app.models.tag import Tag
from app.schemas.tag import TagFiltersSchema
from app.services.base import BaseService
from sqlalchemy.orm import Query


class TagService(BaseService[Tag]):
    model = Tag

    def _apply_filters(
        self, query: Query[Tag], filters: TagFiltersSchema
    ) -> Query[Tag]:
        if filters.name is not None:
            query = query.filter(self.model.name.ilike(f"%{filters.name}%"))
        return query
