# @author owhoyt
from AMSException import AMSException


class AMSConfigException(AMSException):
    def __init__(self, message):
        super(AMSConfigException, self).__init__(message)