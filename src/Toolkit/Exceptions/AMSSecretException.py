# @author owhoyt
from AMSException import AMSException


class AMSSecretException(AMSException):
    def __init__(self, message):
        super(AMSSecretException, self).__init__(message)