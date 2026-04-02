# @author owhoyt
from AMSException import AMSException

class AMSValidationExceptionDefault(Exception):
    def __init__(self, value):
        self.value = value
        super(AMSValidationExceptionDefault, self).__init__('Not a real exception (sorry)')