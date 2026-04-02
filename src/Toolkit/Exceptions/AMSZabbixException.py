# @author owhoyt
from AMSException import AMSException


class AMSZabbixException(AMSException):
    def __init__(self, message):
        super(AMSZabbixException, self).__init__(message)