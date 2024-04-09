"""Repository for Tag model"""

from sqlalchemy.orm import Query

from refinance.models.tag import Tag
from refinance.repository.base import BaseRepository
from refinance.schemas.tag import TagFiltersSchema


class TagRepository(BaseRepository[Tag]):
    model = Tag

    def _apply_filters(self, query: Query, filters: TagFiltersSchema) -> Query:
        if filters.name is not None:
            query = query.filter(self.model.name.ilike(f"%{filters.name}%"))
        return query
