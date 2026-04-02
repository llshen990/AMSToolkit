# @author owhoyt
class LogException(Exception):
    def __init__(self, message):
        super(LogException, self).__init__(message)