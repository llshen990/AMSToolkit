from AMSException import AMSException


class AMSADLSException(AMSException):
    def __init__(self, message):
        super(AMSADLSException, self).__init__(message)