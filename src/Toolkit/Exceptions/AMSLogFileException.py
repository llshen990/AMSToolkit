# @author owhoyt
from AMSException import AMSException


class AMSLogFileException(AMSException):
    def __init__(self, message):
        super(AMSLogFileException, self).__init__(message)