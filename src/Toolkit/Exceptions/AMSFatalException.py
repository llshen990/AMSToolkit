# @author owhoyt
from AMSException import AMSException

class AMSFatalException(AMSException):
    def __init__(self, message):
        super(AMSFatalException, self).__init__(message)