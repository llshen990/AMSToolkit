# @author owhoyt
from AMSException import AMSException


class AMSConfigModelAttributeException(AMSException):
    def __init__(self, message):
        super(AMSConfigModelAttributeException, self).__init__(message)