# @author owhoyt
class EmailSuccessException(Exception):
    def __init__(self, message):
        super(EmailSuccessException, self).__init__(message)