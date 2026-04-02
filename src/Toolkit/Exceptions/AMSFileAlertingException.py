from AMSException import AMSException


class AMSFileAlertingException(AMSException):
    def __init__(self, message):
        super(AMSFileAlertingException, self).__init__(message)