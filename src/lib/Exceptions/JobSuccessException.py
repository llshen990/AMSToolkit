# @author owhoyt
class JobSuccessException(Exception):
    def __init__(self, message):
        super(JobSuccessException, self).__init__(message)