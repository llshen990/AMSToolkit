
from Toolkit.Lib.AbstractAMSReturnCode import AbstractAMSReturnCode

class AMSReturnCode(AbstractAMSReturnCode):
    """
    This class represents a basic return code with a message.
    """

    def __init__(self, subject='', success=False, message=''):
        """
        :param subject:
        :type:  str
        :param success:
        :type:  bool
        :param message:
        :type: str
        """
        AbstractAMSReturnCode.__init__(self, subject)
        self.message = message
        self.job_success = success



