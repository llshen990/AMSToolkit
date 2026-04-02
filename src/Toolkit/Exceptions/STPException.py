# @author owhoyt
from AMSException import AMSException

class STPException(AMSException):
    def __init__(self, message):
        super(STPException, self).__init__(message)