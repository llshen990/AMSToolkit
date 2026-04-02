# @author owhoyt
class AutomationException(Exception):
    def __init__(self, message):
        super(AutomationException, self).__init__(message)