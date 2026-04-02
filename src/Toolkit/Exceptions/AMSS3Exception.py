from AMSException import AMSException


class AMSS3Exception(AMSException):
    def __init__(self, message):
        super(AMSS3Exception, self).__init__(message)