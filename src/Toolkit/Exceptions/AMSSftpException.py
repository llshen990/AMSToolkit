# @author owhoyt
from AMSException import AMSException


class AMSSftpException(AMSException):
    def __init__(self, message):
        super(AMSSftpException, self).__init__(message)