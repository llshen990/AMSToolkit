# @author owhoyt
from StopBatchTriggerZabbixBatchDelayException import StopBatchTriggerZabbixBatchDelayException

class CompressionException(StopBatchTriggerZabbixBatchDelayException):
    def __init__(self, message):
        super(CompressionException, self).__init__(message)