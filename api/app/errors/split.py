"""Split usage errors"""

from app.errors.base import ApplicationError


class PerformedSplitCanNotBeEdited(ApplicationError):
    error_code = 6002
    error = "Can not edit a performed split."


class PerformedSplitCanNotBeDeleted(ApplicationError):
    error_code = 6003
    error = "Can not delete a performed split."


class SplitParticipantAlreadyAdded(ApplicationError):
    error_code = 6004
    error = "Entity already participants in split."


class SplitParticipantAlreadyRemoved(ApplicationError):
    error_code = 6005
    error = "Entity does not participate in split."


class SplitDoesNotHaveParticipants(ApplicationError):
    error_code = 6006
    error = "Split does not have participants."
