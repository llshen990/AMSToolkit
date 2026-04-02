# @author owhoyt
from StopBatchTriggerZabbixBatchDelayException import StopBatchTriggerZabbixBatchDelayException

class FileExistsException(StopBatchTriggerZabbixBatchDelayException):
    def __init__(self, message):
        super(FileExistsException, self).__init__(message)