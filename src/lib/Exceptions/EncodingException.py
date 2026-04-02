# @author owhoyt
from StopBatchTriggerZabbixBatchDelayException import StopBatchTriggerZabbixBatchDelayException

class EncodingException(StopBatchTriggerZabbixBatchDelayException):
    def __init__(self, message):
        super(EncodingException, self).__init__(message)