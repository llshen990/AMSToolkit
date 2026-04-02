# @author owhoyt
class JobException(Exception):
    def __init__(self, message):
        super(JobException, self).__init__(message)