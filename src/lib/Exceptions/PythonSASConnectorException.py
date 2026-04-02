# @author owhoyt
class PythonSASConnectorException(Exception):
    def __init__(self, message):
        super(PythonSASConnectorException, self).__init__(message)