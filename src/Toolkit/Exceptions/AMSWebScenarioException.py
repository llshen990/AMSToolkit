# @author owhoyt
from AMSException import AMSException


class AMSWebScenarioException(AMSException):
    def __init__(self, message):
        super(AMSWebScenarioException, self).__init__(message)