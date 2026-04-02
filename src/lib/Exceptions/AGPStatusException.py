# @author owhoyt
class AGPStatusException(Exception):
    def __init__(self, message):
        super(AGPStatusException, self).__init__(message)