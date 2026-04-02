# @author owhoyt
class EmailSkipException(Exception):
    def __init__(self, message):
        super(EmailSkipException, self).__init__(message)