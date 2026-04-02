# @author owhoyt
class SuccessfulStopValidationException(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super(SuccessfulStopValidationException, self).__init__(message)