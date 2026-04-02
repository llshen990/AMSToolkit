# @author owhoyt
from AMSException import AMSException


class AMSJibbixOptionsException(AMSException):
    def __init__(self, message):
        super(AMSJibbixOptionsException, self).__init__(message)