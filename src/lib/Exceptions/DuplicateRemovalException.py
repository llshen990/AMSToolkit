# @author owhoyt
from StopBatchTriggerZabbixBatchDelayException import StopBatchTriggerZabbixBatchDelayException

class DuplicateRemovalException(StopBatchTriggerZabbixBatchDelayException):
    def __init__(self, message):
        super(DuplicateRemovalException, self).__init__(message)