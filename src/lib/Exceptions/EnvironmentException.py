# @author owhoyt
class EnvironmentException(Exception):
    def __init__(self, message):
        super(EnvironmentException, self).__init__(message)