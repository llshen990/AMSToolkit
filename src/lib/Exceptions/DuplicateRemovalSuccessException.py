# @author owhoyt
class DuplicateRemovalSuccessException(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super(DuplicateRemovalSuccessException, self).__init__(message)