# @author owhoyt
from AMSException import AMSException

class AMSExceptionNoEventNotification(AMSException):
    def __init__(self, message):
        super(AMSExceptionNoEventNotification, self).__init__(message)