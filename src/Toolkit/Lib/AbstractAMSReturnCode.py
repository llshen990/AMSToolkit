import logging
from Toolkit.Lib.Helpers import OutputFormatHelper


class AbstractAMSReturnCode(object):
    """
    This class is the base class of any application specific return code object.
    """

    def __init__(self, subject):
        # holds a list of errors
        self.error_ary = []
        self.failed_jobs = []
        self.message = ""
        self.job_success = False
        self.subject = subject

    def add_result(self, return_code):
        """
        :param return_code: Loaded AbstractAMSReturnCode object.
        :type return_code: AbstractAMSReturnCode
        """
        self.error_ary += return_code.get_error()
        self.job_success &= return_code.is_success()
        self.add_message(return_code.get_message())

    def add_error(self, error_message):
        """
        Adds an error message to the internal errors list in order to keep track of all errors.
        :param error_message: error message to add to internal list.
        :type error_message: str
        :return: True upon success
        :rtype: bool
        """
        error_message = str(error_message).strip()
        self.error_ary.append(error_message)
        self.job_success = False
        return True

    def add_message(self, message):
        """
        Adds an error message to the internal errors list in order to keep track of all errors.
        :param message: error message to add to internal list.
        :type message: str
        :return: True upon success
        :rtype: bool
        """
        message = str(message).strip()
        self.message = self.message + "\n" + message
        return True

    def get_message(self):
        return self.message

    def is_error(self):
        """
        This method will return whether or not the process completed with an error
        :return: boolean value.
        :rtype: bool
        """
        return not self.job_success

    def set_result(self, result):
        self.job_success = result

    def is_success(self):
        """
        This method will return whether or not the process completed successfully
        :return: boolean value.
        :rtype: bool
        """
        return self.job_success

    def get_error(self):
        """
        This method will return all errors, if any
        :return: list of Strings of errors.
        :rtype: list
        """
        return self.error_ary

    def get_failed_jobs(self):
        """
        This method will return all failed jobs, if any
        :return: list of Strings of failed jobs.
        :rtype: list
        """
        return self.failed_jobs

    def format_failed_jobs(self):
        """
        This method will take all failed jobs, if any, and return a formatted string of the failed jobs
        :return: String of failed jobs separated by a comma.
        :rtype: str
        """
        if not self.failed_jobs:
            return ""
        return OutputFormatHelper.join_output_from_list(self.failed_jobs, ', ')

    def format_errors(self):
        """
        This method will take all errors, if any, and return a formatted string of the errors
        :return: String of errors separated by EOL char.
        :rtype: str
        """
        if not self.error_ary:
            return ""
        return OutputFormatHelper.join_output_from_list(self.error_ary)

    def format_error_summary(self):
        return "%s: failed | return status: %s" % (self.subject, self.job_success)

    def display_job_status(self):
        if not self.job_success:
            logging.getLogger('AMS').error('Job Status: Found errors {}'.format(self.message))
        logging.getLogger('AMS').info('Job Status: Job success is {}'.format(self.job_success))