# @author owhoyt
from AMSException import AMSException


class AMSMethodException(AMSException):
    def __init__(self, message):
        super(AMSMethodException, self).__init__(message)