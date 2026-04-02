# @author owhoyt
from AMSException import AMSException


class AMSEnvironmentException(AMSException):
    def __init__(self, message):
        super(AMSEnvironmentException, self).__init__(message)