# @author owhoyt
class WarningValidationException(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super(WarningValidationException, self).__init__(message)