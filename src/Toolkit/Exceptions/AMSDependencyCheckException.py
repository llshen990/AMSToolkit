# @author owhoyt
from AMSException import AMSException

class AMSDependencyCheckException(AMSException):
    def __init__(self, message):
        super(AMSDependencyCheckException, self).__init__(message)