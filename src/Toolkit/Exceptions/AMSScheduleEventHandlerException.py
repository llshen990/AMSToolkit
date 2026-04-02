# @author owhoyt
from AMSException import AMSException

class AMSScheduleEventHandlerException(AMSException):
    def __init__(self, message):
        super(AMSScheduleEventHandlerException, self).__init__(message)