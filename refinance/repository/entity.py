from refinance.models.entity import Entity
from refinance.repository.base import BaseRepository


class EntityRepository(BaseRepository[Entity]):
    model = Entity

    def delete(self, obj_id):
        """This will fuck with history, implement it later (maybe)"""
        raise NotImplementedError
