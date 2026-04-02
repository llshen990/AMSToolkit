# @author owhoyt
from AMSException import AMSException

class AMSSSORunLogException(AMSException):
    def __init__(self, message):
        super(AMSSSORunLogException, self).__init__(message)