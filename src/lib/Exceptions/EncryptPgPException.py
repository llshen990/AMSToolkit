# @author owhoyt
from StopBatchTriggerZabbixBatchDelayException import StopBatchTriggerZabbixBatchDelayException

class EncryptPgPException(StopBatchTriggerZabbixBatchDelayException):
    def __init__(self, message):
        super(EncryptPgPException, self).__init__(message)