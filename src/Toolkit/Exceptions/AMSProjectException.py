# @author owhoyt
from AMSException import AMSException


class AMSProjectException(AMSException):
    def __init__(self, message):
        super(AMSProjectException, self).__init__(message)