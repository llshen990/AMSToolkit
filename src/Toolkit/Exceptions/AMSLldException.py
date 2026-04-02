# @author owhoyt
from AMSException import AMSException

class AMSLldException(AMSException):
    def __init__(self, message):
        super(AMSLldException, self).__init__(message)