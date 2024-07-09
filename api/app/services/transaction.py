"""Transaction service"""

from sqlalchemy import or_
from sqlalchemy.orm import Query

from app.models.entity import Entity
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionFiltersSchema
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin


class TransactionService(TaggableServiceMixin[Transaction], BaseService[Transaction]):
    model = Transaction

    def _apply_filters(
        self, query: Query[Transaction], filters: TransactionFiltersSchema
    ) -> Query[Transaction]:
        if filters.entity_id is not None:
            query = query.filter(
                or_(
                    self.model.from_entity_id == filters.entity_id,
                    self.model.to_entity_id == filters.entity_id,
                    self.model.actor_entity_id == filters.actor_entity_id,
                )
            )
        if filters.actor_entity_id is not None:
            query = query.filter(self.model.actor_entity_id == filters.actor_entity_id)
        if filters.from_entity_id is not None:
            query = query.filter(self.model.from_entity_id == filters.from_entity_id)
        if filters.to_entity_id is not None:
            query = query.filter(self.model.to_entity_id == filters.to_entity_id)
        if filters.amount_min is not None:
            query = query.filter(self.model.amount >= filters.amount_min)
        if filters.amount_max is not None:
            query = query.filter(self.model.amount <= filters.amount_max)
        if filters.currency is not None:
            query = query.filter(self.model.currency == filters.currency)
        if filters.comment is not None:
            query = query.filter(self.model.comment.ilike(f"%{filters.comment}%"))
        if filters.confirmed is not None:
            query = query.filter(self.model.confirmed == filters.confirmed)
        return query

    def create(self, schema, actor_entity: Entity) -> Transaction:
        return super().create(schema, overrides={"actor_entity_id": actor_entity.id})
