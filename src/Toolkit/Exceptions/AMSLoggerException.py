# @author owhoyt
class AMSLoggerException(Exception):
    def __init__(self, message):
        super(AMSLoggerException, self).__init__(message)
