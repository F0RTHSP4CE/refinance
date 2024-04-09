"""Mixin of a service which supports item tagging"""

from refinance.repository.mixins.taggable_mixin import TaggableRepositoryMixin
from refinance.services.base import BaseService


class TaggableServiceMixin(BaseService):
    repo: TaggableRepositoryMixin

    def add_tag(self, obj_id: int, tag_id: int):
        return self.repo.add_tag(obj_id, tag_id)

    def remove_tag(self, obj_id: int, tag_id: int):
        return self.repo.remove_tag(obj_id, tag_id)
