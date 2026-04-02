# @author owhoyt
class EmailException(Exception):
    def __init__(self, message):
        super(EmailException, self).__init__(message)