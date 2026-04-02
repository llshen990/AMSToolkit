# @author owhoyt
from StopBatchTriggerZabbixBatchDelayException import StopBatchTriggerZabbixBatchDelayException

class FileShredderException(StopBatchTriggerZabbixBatchDelayException):
    def __init__(self, message):
        super(FileShredderException, self).__init__(message)