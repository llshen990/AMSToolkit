# @author owhoyt
from AMSException import AMSException


class AMSScheduleException(AMSException):
    def __init__(self, message):
        super(AMSScheduleException, self).__init__(message)