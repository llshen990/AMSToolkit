# @author owhoyt
from AMSException import AMSException

class AMSAttributeMapperException(AMSException):
    def __init__(self, message):
        super(AMSAttributeMapperException, self).__init__(message)