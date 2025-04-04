"""Split usage errors"""

from app.errors.base import ApplicationError


class PerformedSplitCanNotBeEdited(ApplicationError):
    error_code = 6002
    error = "Can not edit a performed split."


class PerformedSplitCanNotBeDeleted(ApplicationError):
    error_code = 6003
    error = "Can not delete a performed split."


# not needed anymore, because we just override the data in that case
#
# class SplitParticipantAlreadyAdded(ApplicationError):
#     error_code = 6004
#     error = "Entity is already a participant of this split."


class SplitParticipantAlreadyRemoved(ApplicationError):
    error_code = 6005
    error = "Entity is not a participant of this split."


class SplitDoesNotHaveParticipants(ApplicationError):
    error_code = 6006
    error = "Split does not have participants."


class PerformedSplitParticipantsAreNotEditable(ApplicationError):
    error_code = 6007
    error = "Can not add/remove participants of a performed split."


class MinimalNumberOfParticipantsRequired(ApplicationError):
    error_code = 6008
    error = "There should be at least 1 participants to perform the split."
