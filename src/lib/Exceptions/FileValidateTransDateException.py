# @author owhoyt
from StopBatchTriggerZabbixBatchDelayException import StopBatchTriggerZabbixBatchDelayException

class FileValidateTransDateException(StopBatchTriggerZabbixBatchDelayException):
    def __init__(self, message):
        super(FileValidateTransDateException, self).__init__(message)