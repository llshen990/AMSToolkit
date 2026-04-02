# @author owhoyt
class AGPReportEmailsException(Exception):
    def __init__(self, message):
        super(AGPReportEmailsException, self).__init__(message)