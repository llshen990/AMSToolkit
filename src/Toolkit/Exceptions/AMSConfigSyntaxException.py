# @author owhoyt
from AMSException import AMSException

class AMSConfigSyntaxException(AMSException):
    def __init__(self, message):
        super(AMSConfigSyntaxException, self).__init__(message)