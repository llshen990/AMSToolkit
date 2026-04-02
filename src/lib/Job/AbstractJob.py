# @author owhoyt
import ConfigParser
import abc
import os.path
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from datetime import datetime

from lib.Exceptions import JobException, JobSuccessException
from lib.Signals import Signal
from lib.Helpers import OutputFormatHelper, Logger
from lib.Validators import FileExistsValidator

class AbstractJob(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, sig_path, debug=False, preq_sig=None):
        # set debug
        self._debug = False if not debug else True

        # get config options
        self.signal_prefix = 'job_'
        self.config = ConfigParser.ConfigParser()
        self.config.read(APP_PATH + '/Config/ssod_validator.cfg')

        self.logger = Logger(os.path.join(self.config.get('DEFAULT', 'logs_dir'), str(self) + '_job.log'))

        if not self.config.has_option('DEFAULT', 'global_temp_stop_signal'):
            raise JobException('global_temp_stop_signal does not exist in config')

        if not self.config.has_option('DEFAULT', 'logs_dir'):
            raise JobException('No logs dir defined')

        if not self.config.has_option('DEFAULT', 'base_automation_signal_path'):
            raise JobException('No base automation signal path')

        # prereq signal object
        self.prereq_signal = None  # type: Signal
        if preq_sig is not None:
            if not isinstance(preq_sig, Signal):
                raise JobException('Preq Sig must be an instance of Signal')

            self.prereq_signal = preq_sig

        if not sig_path:
            raise JobException('sig_path is required')

        # path to signals
        self.signal_path = str(sig_path).strip()  # type: str
        self.signal_extension = '.sig'

        # holds full path to job filename
        self.job_path = None  # type: str
        # holds a list of attributes to pass into the job (script etc)
        self.attribute_ary = []
        # holds a list of errors
        self.error_ary = []
        # flag for job started
        self.job_started = False
        # flag for job success
        self.job_success = False
        # flag for job error
        self.job_error = False
        # full path to directory for logs
        self.log_path = None  # type: str
        # external log path of any external scripts
        self.log_path_external = None  # type: str
        # running signal object
        self.running_signal = None  # type: Signal
        # ok signal object
        self.ok_signal = None  # type: Signal
        # stopped signal object
        self.stopped_signal = None  # type: Signal
        # finished signal object
        self.finished_signal = None  # type: Signal
        # global temp stop signal
        temp_stop_filename = self.config.get('DEFAULT', 'global_temp_stop_signal')
        self.global_temp_stop_signal = Signal(os.path.dirname(temp_stop_filename), os.path.basename(temp_stop_filename), True, self.signal_extension)

        self.file_exists_validator = FileExistsValidator(True)
        self.signal_path_txt = ''

        self.archive_file_on_success = False
        self.job_type = 'UNDEFINED_JOB_TYPE'

    @abc.abstractmethod
    def get_job_name(self):
        """
        Returns the user friendly job name
        :return: String of job name
        :rtype: str 
        """
        return

    def get_signal_job_name(self):
        """
        Returns the user friendly job name to be used in the signal file
        :return: String of job name
        :rtype: str 
        """
        ret_str = str(self)
        if self.signal_path != '':
            ret_str += '_' + self.signal_path_txt
        return ret_str

    @abc.abstractmethod
    def detect_error(self):
        return

    @abc.abstractmethod
    def run_job(self):
        return

    def stop_job(self):
        """
        This method will look at the self.job_error member variable to determine if there are errors.  If so, it will write out
        the errors to the stopped signal and throw a JobException.
        :return: True upon success
        :rtype: bool
        """
        if self.job_error:
            self.ok_signal.remove_signal()
            error_str = OutputFormatHelper.join_output_from_list(self.error_ary)
            self.stopped_signal.write_signal_and_data('Stopping job due to errors at ' + str(datetime.now()) + os.linesep + error_str)
            raise JobException('There was an error running job ' + self.get_job_name() + ':' + os.linesep + error_str)
        return True

    def start_job(self):
        """
        This method is the main controller for running a job.  External classes should call into this to start this job.
        :return: True upon success
        :rtype: bool
        """

        try:
            self.init_signals()

            self.ok_to_run()

            if not self.running_signal.exists():
                self.running_signal.write_signal_and_data('STARTED|' + str(datetime.now()))

            # time.sleep(60)

            self.job_started = 1
            self.ok_signal.write_signal_and_data('Starting execution of core job logic at ' + str(datetime.now()))
            self.run_job()
            self.detect_error()
            # if 1 or self.signal_path_txt.find('fscRunAMLJob_48') == -1: # @todo: remove debug
            #     self.job_error = False  # @todo: remove debug
            #     self.job_success = True # @todo: remove debug

            self.stop_job()
            self.complete_job()
        except JobSuccessException as e:
            print str(e)
            raise e
        except Exception as e:
            raise e
        finally:
            self.running_signal.remove_signal()

    def add_attribute(self, attribute):
        """
        :param attribute: Attribute to add to internal attributes array to be passed into job
        :type attribute: mixed
        :return: True on success
        :rtype: bool
        """
        attribute = str(attribute).strip()
        attribute = None if attribute == '' else attribute
        if not attribute:
            raise JobException('Attribute required')

        self.attribute_ary.append(attribute)
        return True

    def add_error(self, error_message):
        """
        Adds an error message to the internal errors list in order to keep track of all errors.
        :param error_message: error message to add to internal list.
        :type error_message: str
        :return: True upon success
        :rtype: bool
        """
        error_message = '[JOB_ERROR] ' + str(error_message).strip()
        if error_message == '':
            raise JobException('Error message required')
        self.log_it(error_message)
        self.error_ary.append(error_message)

        return True

    def get_errors(self):
        """
        This method will return the list of errors
        :return: list of errors
        :rtype: list
        """
        return self.error_ary

    def format_errors(self):
        """
        This method will take all errors, if any, and return a formatted string of the errors
        :return: String of errors separated by EOL char.
        :rtype: str
        """
        if len(self.error_ary) == 0:
            return ""
        return OutputFormatHelper.join_output_from_list(self.error_ary)

    def reset_errors(self):
        """
        This method will reset the error list.
        :return: True upon success.
        :rtype: bool
        """
        self.error_ary = []
        return True

    def complete_job(self):
        """
        Sets success to True and raises JobSuccessException.
        """
        self.job_success = True
        msg = 'Job ' + str(self) + ' completed successfully.'
        self.log_it(msg)
        self.finished_signal.write_signal_and_data('FINISHED|' + str(datetime.now()))
        raise JobSuccessException(msg)

    def init_signals(self):
        """
        This method will init all signal objects to be used in this job object.
        :return: True upon success.
        :rtype: bool
        """
        self.running_signal = Signal(self.signal_path, self.signal_prefix + self.get_signal_job_name().lower() + '_running', True, self.signal_extension)
        # self.log_it('Initiating signal running_signal object: ' + self.running_signal.full_file_path)
        self.ok_signal = Signal(self.signal_path, self.signal_prefix + self.get_signal_job_name().lower() + '_ok', True, self.signal_extension)
        # self.log_it('Initiating signal ok_signal object: ' + self.ok_signal.full_file_path)
        self.stopped_signal = Signal(self.signal_path, self.signal_prefix + self.get_signal_job_name().lower() + '_stopped', True, self.signal_extension)
        # self.log_it('Initiating signal stopped_signal object: ' + self.stopped_signal.full_file_path)
        self.finished_signal = Signal(self.signal_path, self.signal_prefix + self.get_signal_job_name().lower() + '_finished', True, self.signal_extension)
        # self.log_it('Initiating signal finished_signal object: ' + self.finished_signal.full_file_path)
        return True

    def ok_to_run(self):
        """
        This method will determine if the current job is ok to run based on the current state of the signals.
        :return: True upon success
        :rtype: bool
        """
        job_stopped_messages = []

        if self.finished_signal.exists():
            raise JobSuccessException('[JOB][FINISHED] Job finished signal is set, skipping job: ' + self.finished_signal.full_file_path)

        if self.stopped_signal.exists():
            job_stopped_messages.append('[JOB][ERROR] Stop signal due to error signal is set: ' + self.stopped_signal.full_file_path)

        if self.global_temp_stop_signal.exists():
            job_stopped_messages.append('[JOB][STOPPED] global temp stop is set: ' + self.global_temp_stop_signal.full_file_path)

        if self.prereq_signal and not self.prereq_signal.exists():
            job_stopped_messages.append('[JOB][PREQ_NOT_DONE] the prerequisite signal is not yet set: ' + self.prereq_signal.full_file_path)

        if self.running_signal.exists():
            job_stopped_messages.append('[JOB][RUNNING] the current job is already running and the signal is set: ' + self.running_signal.full_file_path)

        if len(job_stopped_messages) > 0:
            raise JobException(OutputFormatHelper.join_output_from_list(job_stopped_messages, Signal.get_join_separator()))

        return True

    def log_it(self, message):
        """
        If debug is on, will write a message to terminal + log file.  If off, it will only write to log file.
        :param message: Message to write to log.
        :type message: str
        :return: True upon completion
        :rtype: bool
        """
        try:
            self.logger.write_debug(OutputFormatHelper.log_msg_with_time(message), self._debug)
        except Exception as e:
            raise JobException(str(e))

        return True

    def __str__(self):
        """magic method when you call print({job}) to print the name of the job"""
        return self.__class__.__name__

    def __del__(self):
        """This is the destructor for all Jobs"""
        if self.logger:
            self.logger.close_logger()
        return