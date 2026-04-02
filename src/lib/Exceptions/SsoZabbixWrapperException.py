# @author owhoyt
class SsoZabbixWrapperException(Exception):
    def __init__(self, message):
        super(SsoZabbixWrapperException, self).__init__(message)