# @author owhoyt
from StopBatchTriggerZabbixBatchDelayException import StopBatchTriggerZabbixBatchDelayException

class ManifestCreateException(StopBatchTriggerZabbixBatchDelayException):
    def __init__(self, message):
        super(ManifestCreateException, self).__init__(message)