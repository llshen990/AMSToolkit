# @author owhoyt
from AMSException import AMSException

class AMSEventHandlerException(AMSException):
    def __init__(self, message):
        super(AMSEventHandlerException, self).__init__(message)