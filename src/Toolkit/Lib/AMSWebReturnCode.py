import re
import socket

from Toolkit.Lib.AbstractAMSReturnCode import AbstractAMSReturnCode

class AMSWebReturnCode(AbstractAMSReturnCode):
    """
    This class encapsulates the functionality for returning a values from a process exec.
    It contains the pid, process rc, and contents of stdout and stderr.
    """

    def __init__(self, url):
        AbstractAMSReturnCode.__init__(self, url)
        self.url = url  # type:str
        self.data = None  # type:str
        self.status_code = None  # type:str

    def __str__(self):
        return self.__class__.__name__ + "[url=" + str(self.url) + ", status_code=" + str(self.status_code) + ", job_success=" + str(self.job_success) + ", message=" + self.message + "]"

        # @todo: create member variables that map to a web response.  Then retrofit the below methods or remove them if they don't make sense.
    # def detect_errors(self):
    #     """
    #     This method will detect errors in the job unless an exception occurs.
    #     :return:
    #     :rtype:
    #     """
    #     self.job_success = True
    #     if self.std_err != "":
    #         self.add_error(AMSWebReturnCode.ERROR_PREFIX + ' (std_error output): ' + str(self.std_err))
    #         self.job_success = False
    #
    #     if self.returncode > 0:
    #         self.add_error(AMSWebReturnCode.ERROR_PREFIX + ' (return_code > 0): ' + str(self.returncode))
    #         self.job_success = False
    #
    #     pattern = re.compile('|'.join(self.error_pattern_list))
    #     errors = pattern.findall(self.std_out)
    #
    #     if len(errors) > 0:
    #         self.add_error(AMSWebReturnCode.ERROR_PREFIX + ' (std_out output): ' + str(self.std_out))
    #         self.job_success = False
    #
    #     return True
    #
    # def get_message(self):
    #     return "Process pid=" + str(self.pid) + " script_path=" + str(self.subject) + " success=" + str(self.is_success())
    #
    # def get_pid(self):
    #     """
    #     This method will return the process id of the completed process
    #     :return: the integer pid value from the subprocess call.
    #     :rtype: int
    #     """
    #     return self.pid
    #
    # def get_returncode(self):
    #     """
    #     This method will return the returncode of the completed process
    #     :return: the integer returncode value from the subprocess call.
    #     :rtype: int
    #     """
    #     return self.returncode
    #
    # def format_error_summary(self):
    #     return "%s: Script \'%s\' failed | return code: %s" % (self.hostname, self.script_name, self.returncode)