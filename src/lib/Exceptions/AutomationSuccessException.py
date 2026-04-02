# @author owhoyt
class AutomationSuccessException(Exception):
    def __init__(self, message):
        super(AutomationSuccessException, self).__init__(message)