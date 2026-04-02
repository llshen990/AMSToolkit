# @author owhoyt
class DailyBatchAutomationStatusException(Exception):
    def __init__(self, message):
        super(DailyBatchAutomationStatusException, self).__init__(message)