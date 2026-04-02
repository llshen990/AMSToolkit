# @author owhoyt
from AMSException import AMSException


class AMSOlaException(AMSException):
    def __init__(self, message):
        super(AMSOlaException, self).__init__(message)