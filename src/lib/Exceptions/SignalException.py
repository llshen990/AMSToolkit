# @author owhoyt
class SignalException(Exception):
    def __init__(self, message):
        super(SignalException, self).__init__(message)