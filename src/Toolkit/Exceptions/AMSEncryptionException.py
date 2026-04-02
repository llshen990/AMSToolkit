from AMSException import AMSException


class AMSEncryptionException(AMSException):
    def __init__(self, message):
        super(AMSEncryptionException, self).__init__(message)
