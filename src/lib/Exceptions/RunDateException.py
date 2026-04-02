# @author owhoyt
class RunDateException(Exception):
    def __init__(self, message):
        super(RunDateException, self).__init__(message)