"""Tag usage errors"""

from app.errors.base import ApplicationError


class TagAlreadyAdded(ApplicationError):
    error_code = 2001
    error = "Tag already added"


class TagAlreadyRemoved(ApplicationError):
    error_code = 2002
    error = "Tag already removed"


class TagsNotSupported(ApplicationError):
    error_code = 2003
    error = "Tag functionality is unavailable for this component, but methods are present. WTF?"


class TagIsBusy(ApplicationError):
    error_code = 2004
    error = "Tag is being used by some object(s)"
