# @author owhoyt
class OutputFormatHelperException(Exception):
    def __init__(self, message):
        super(OutputFormatHelperException, self).__init__(message)