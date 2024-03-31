"""Repository for Entity model"""

from refinance.models.entity import Entity
from refinance.repository.base import BaseRepository


class EntityRepository(BaseRepository[Entity]):
    model = Entity

    def delete(self, obj_id):
        """This will break the history, implement it later (maybe)"""
        raise NotImplementedError
