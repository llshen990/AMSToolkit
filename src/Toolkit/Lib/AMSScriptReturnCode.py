import os.path

import re
import logging

from Toolkit.Lib.AbstractAMSReturnCode import AbstractAMSReturnCode
from Toolkit.Lib.Defaults import AMSDefaults


class AMSScriptReturnCode(AbstractAMSReturnCode):
    """
    This class encapsulates the functionality for returning a values from a process exec.
    It contains the pid, process rc, and contents of stdout and stderr.
    """

    ERROR_PREFIX = '[JOB_ERROR] There was an error running this job'

    OS_ERROR_CODES = {
        '.*Errno 8.*': '*** It looks like the script that is scheduled can not be interpreted. ' \
                                'This error may be caused by a missing shebang at the beginning of the script.  ***',
        '.*Errno 13.*': '*** The user may be missing execute permission on the script. ' \
                                'Please try chmod u+x <script-name> to correct it. ***'
    }

    def __init__(self, pid, returncode, std_out, std_err, script_name):
        AbstractAMSReturnCode.__init__(self, script_name)
        # the pid of the completed process
        self.pid = pid
        self.std_err = std_err
        self.std_out = std_out
        self.returncode = returncode
        self.script_name = script_name
        if self.returncode > 0:
            self.job_success = False
        else:
            self.job_success = True

        # detect any errors on stdout/err and set job_success as needed
        self.detect_errors()

    def detect_errors(self):
        """
        This method will detect errors in the job unless an exception occurs.
        :return:
        :rtype:
        """
        self.job_success = True
        prefix = os.path.basename(self.script_name).upper()

        num_asterisks = 30
        if self.std_err != "":
            self.std_err = '[{}]'.format(prefix).join(self.std_err.splitlines(True))
            self.std_err = '{}{}STDERR-BEGIN{}{}[{}]{}{}{}STDERR-END{}'.format(os.linesep, num_asterisks*'*', num_asterisks*'*', os.linesep, prefix, self.std_err, os.linesep, (num_asterisks+2)*'*', num_asterisks*'*')

            self.add_error(AMSScriptReturnCode.ERROR_PREFIX + ' (std_error output): ' + str(self.std_err))
            self.job_success = False
            self.explain_os_errors()

        if self.std_out != "":
            self.std_out = '[{}]'.format(prefix).join(self.std_out.splitlines(True))
            self.std_out = '{}{}STDOUT-BEGIN{}{}[{}]{}{}{}STDOUT-END{}'.format(os.linesep, num_asterisks*'*', num_asterisks*'*', os.linesep, prefix, self.std_out, os.linesep, (num_asterisks+2)*'*', num_asterisks*'*')

        if self.returncode > 0:
            self.add_error(AMSScriptReturnCode.ERROR_PREFIX + ' (return_code > 0): ' + str(self.returncode))
            self.job_success = False

        return self.job_success

    def explain_os_errors(self):
        """
            This method adds more context to OSError, triggered by subprocess.Popen
            For some reason when Popen encounters an OSError, it only prints the error message to stdout without
            raising a runtime error.
            This method parses the output to stdout and attempts to add the lost context back.
        """
        for code in self.OS_ERROR_CODES:
            pattern = re.compile(code)
            if pattern.search(self.std_err):
                self.add_error(self.OS_ERROR_CODES[code])

    def display_job_status(self):
        if not self.job_success:
            if self.std_err != "":
                logging.getLogger('AMS').error('Job Status: Found stderr output {}'.format(self.std_err))

            if self.returncode > 0:
                logging.getLogger('AMS').error('Job Status: Return code {} > 0'.format(self.returncode))

        AbstractAMSReturnCode.display_job_status(self)

    def get_message(self):
        if self.message:
            return self.message
        else:
            return "Process pid=" + str(self.pid) + " script_path=" + str(self.subject) + " success=" + str(self.is_success())

    def get_pid(self):
        """
        This method will return the process id of the completed process
        :return: the integer pid value from the subprocess call.
        :rtype: int
        """
        return self.pid

    def get_returncode(self):
        """
        This method will return the returncode of the completed process
        :return: the integer returncode value from the subprocess call.
        :rtype: int
        """
        return self.returncode

    def format_error_summary(self):
        return "%s: Script \'%s\' failed | return code: %s" % (AMSDefaults().my_hostname, self.script_name, self.returncode)