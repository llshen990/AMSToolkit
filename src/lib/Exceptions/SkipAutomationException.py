# @author owhoyt
class SkipAutomationException(Exception):
    def __init__(self, message):
        super(SkipAutomationException, self).__init__(message)