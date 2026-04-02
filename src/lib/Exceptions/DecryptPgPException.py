# @author owhoyt
from StopBatchTriggerZabbixBatchDelayException import StopBatchTriggerZabbixBatchDelayException

class DecryptPgPException(StopBatchTriggerZabbixBatchDelayException):
    def __init__(self, message):
        super(DecryptPgPException, self).__init__(message)