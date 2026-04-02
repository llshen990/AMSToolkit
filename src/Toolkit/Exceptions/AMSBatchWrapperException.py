# @author owhoyt
from AMSException import AMSException


class AMSBatchWrapperException(AMSException):
    def __init__(self, message):
        super(AMSBatchWrapperException, self).__init__(message)