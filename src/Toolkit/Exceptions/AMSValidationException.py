# @author owhoyt
from AMSException import AMSException

class AMSValidationException(Exception):
    def __init__(self, message):
        super(AMSValidationException, self).__init__(message)