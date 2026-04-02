# @author owhoyt
class SkipValidationException(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super(SkipValidationException, self).__init__(message)