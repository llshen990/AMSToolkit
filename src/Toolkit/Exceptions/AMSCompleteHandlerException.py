# @author owhoyt
from AMSException import AMSException

class AMSCompleteHandlerException(AMSException):
    def __init__(self, message):
        super(AMSCompleteHandlerException, self).__init__(message)