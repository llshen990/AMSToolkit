# @author owhoyt
import ConfigParser
import abc
import glob
import os.path
import shutil
import sys
import time
import traceback

from lib.Exceptions import AutomationException, AutomationSuccessException, JobSuccessException, JobException, SkipAutomationException
from lib.Helpers import OutputFormatHelper, RunDate, Md5Sum
from lib.Job import *
from lib.Signals import Signal
from datetime import datetime, timedelta
from lib.Validators import FileExistsValidator
from AbstractScenario import AbstractScenario

class AbstractAutomation(AbstractScenario):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        AbstractScenario.__init__(self, debug=False)

        # prefixes all signals written / read
        self.signal_prefix = 'automation_'
        self.signal_extension = '.sig'

        # set some defaults / setup some config data
        self.config = ConfigParser.ConfigParser()
        self.config.read(AbstractScenario.APP_PATH + '/Config/ssod_validator.cfg')

        if not self.config.has_option('DEFAULT', 'global_temp_stop_signal'):
            raise AutomationException('global_temp_stop_signal does not exist in config')

        if not self.config.has_option('DEFAULT', 'logs_dir'):
            raise AutomationException('No logs dir defined in config.')

        if not self.config.has_option('DEFAULT', 'base_automation_signal_path'):
            raise AutomationException('No base automation signal path in config.')

        if not self.config.has_option('DEFAULT', 'landingdir'):
            raise AutomationException('No landingdir path specified in config.')

        if not self.config.has_option('DEFAULT', 'archivedir'):
            raise AutomationException('No archivedir path specified in config.')

        if not self.config.has_option('DEFAULT', 'market_config_section'):
            raise AutomationException('No market_config_section path specified in config.')

        # What market this code is running in.
        self.market = self.config.get('DEFAULT', 'market_config_section')

        # whether or not to check DQ signals.
        self.enable_dq_dependency = False
        self.dq_signal_dir = None
        if self.config.has_option(self.market, 'validation_output_dir'):
            self.enable_dq_dependency = True
            self.dq_signal_dir = self.config.get(self.market, 'validation_output_dir')

        # set the landing directory for the files.
        self.file_landing_dir = self.config.get('DEFAULT', 'landingdir')
        # set the landing directory for the files.
        self.file_archive_dir = os.path.join(self.config.get('DEFAULT', 'archivedir'), str(self))

        # filename patterns to match this automation
        """:type: dict[str, dict] """
        self.filename_patterns = {}
        # current file to process
        self.current_file_to_process = None  # type: str
        # current file's manifest:
        self.current_manifest_to_process = None  # type: str

        # prefix of manifest files
        self.manifest_prefix = 'manifest.'
        # prefix of file (if manifest is enabled)
        self.file_prefix = 'file.'

        # list of job objects
        self.remaining_jobs_list = []
        # holds the Job object of the current Job
        self.current_job = None  # type: AbstractJob
        # holds the list of jobs that have completed successfully.
        self.jobs_run_list = []

        # path to signal directory
        self.signal_path = os.path.join(self.config.get('DEFAULT', 'base_automation_signal_path'), str(self))

        ##### Start Run Date #####

        # holds the run date of which files should be run (optional)
        self.run_date = None  # type: RunDate
        # tells the automation if it needs to use a specific run date
        self.has_run_date = None
        # format of run date (probably relates to filename in some way)
        self.run_date_format = '%Y%m%d'
        ##### End Run Date #####
        # holds a list of errors
        self.error_ary = []
        # holds the error string
        self.error_str = ''
        # directory where logs should go
        self.logs = None
        # flag of whether or not automation has 'started'
        self.automation_started = False
        # start datetime object
        self.automation_start_dt = None  # type: datetime
        # flag of whether or not automation has finished 'successfully'
        self.automation_success = False
        # flag of whether or not automation has an error
        self.automation_error = False
        # automation end date datetime object.  Could be finished or error.
        self.automation_end_dt = None  # type: datetime
        # Auto Jira object to fire on failure (optional)
        self.auto_jira_fail_obj = None
        # Auto Jira object to fire on success (optional)
        self.auto_jira_success_obj = None

        #### signals start ####
        # running signal object
        self.running_signal = None  # type: Signal
        # ok signal object
        self.ok_signal = None  # type: Signal
        # stopped signal object
        self.stopped_signal = None  # type: Signal
        # dq passed signal object
        self.dq_passed_signal = None  # type: Signal
        # dq failed signal object
        self.dq_failed_signal = None  # type: Signal
        # finished signal object
        self.finished_signal = None  # type: Signal
        # finished signal object
        self.temp_stop_signal = None  # type: Signal
        # global temp stop signal
        temp_stop_filename = self.config.get('DEFAULT', 'global_temp_stop_signal')
        temp_stop_filename_tmp, temp_stop_extension_tmp = os.path.splitext(temp_stop_filename)
        self.global_temp_stop_signal = Signal(os.path.dirname(temp_stop_filename), os.path.basename(temp_stop_filename), True, temp_stop_extension_tmp)
        #### signals end ####

        # init the file name patterns.  This should be a dictionary (dict) that is in the following format:
        # self.filename_patterns = {
        #     'mx_wc_usd': {
        #         'file_pattern': 'file.*.mex.mx_wc.mx_wc_usd_{FILEDATE}.txt.pgp',
        #         'manifest_pattern': 'manifest.*.mex.mx_wc.mx_wc_usd_{FILEDATE}.txt.pgp',
        #         'num': 1,
        #         'found_files': [],
        #         'files_to_validate': [],
        #         'files_to_process': []
        #     }
        # }
        self.set_filename_patterns()
        # total number of files to process
        self.total_files_to_process = 0
        # total number of files found that may be eligible to process
        self.total_files_found = 0

        # email list for automation emails
        self.automation_email_list = None  # type: str
        if self.config.has_option('DEFAULT', 'automation_email_list'):
            self.automation_email_list = self.config.get('DEFAULT', 'automation_email_list')

    @abc.abstractmethod
    def init_jobs(self):
        return

    @abc.abstractmethod
    def get_run_date_of_file(self, filename):
        return

    @abc.abstractmethod
    def automation_success_handler(self):
        return

    @abc.abstractmethod
    def automation_error_handler(self):
        return

    @abc.abstractmethod
    def automation_start_handler(self):
        return

    @abc.abstractmethod
    def find_available_files(self):
        return

    @abc.abstractmethod
    def set_filename_patterns(self):
        return

    @abc.abstractmethod
    def validate_eligible_fies(self):
        return

    def start_automation(self):
        """
        This method is the main entry point and is called from automation_controller.py
        """
        try:
            self.log_it('------------------------ STARTING AUTOMATION -------------------------------')

            # 2: we init the signals.
            self.log_it('Initiating signals...')
            self.init_signals()

            self.log_it('Checking signal state, are we ok to run?')
            self.ok_to_run()
            if not self.running_signal.exists():
                self.automation_start_dt = datetime.now()
                self.running_signal.write_signal_and_data('STARTED|' + str(datetime.now()))
            else:
                self.automation_start_dt = datetime.now()  # @todo: parse self.running_signal to get the started date.

            # 1: Get run dates (if necessary)
            self.log_it('Getting last and current run dates...')
            self.init_run_dates()

            # 3: find all matching files (if any)
            self.log_it('Finding available files...')
            if not self.find_available_files():
                self.log_it('Removing running signal...')
                self.running_signal.remove_signal()
                raise SkipAutomationException(OutputFormatHelper.join_output_from_list(['[AUTOMATION][SKIPPED] Incomplete batch set of files.'], Signal.get_join_separator()))

            # check if we have any files available to process
            if self.total_files_found < 1:
                self.log_it('Removing running signal...')
                self.running_signal.remove_signal()
                raise SkipAutomationException(OutputFormatHelper.join_output_from_list(['[AUTOMATION][SKIPPED] No files found as number of found files is zero'], Signal.get_join_separator()))

            # 3: we check if we're ok to run.  This will handle looking at all the signals and determining what state we are in
            # within the overall automation.  This will not determine which job should be run in terms of resuming.
            # the ok_to_run() method will also throw the proper exception, so no need to handle it here.

            self.log_it('Determine if available files are ok to run and match the run date (if applicable)')
            self.get_eligible_files_for_this_run()

            self.log_it('Validating eligible files')
            self.validate_eligible_fies()

            self.automation_started = True
            self.automation_start_handler()
            self.ok_signal.write_signal_and_data('Starting execution of core automation logic at ' + str(self.automation_start_dt))

            # 5: we actually now run the jobs.
            self.log_it('Starting jobs...')
            self.start_jobs()

            # 6: we finalize the automation.  In the finalize_automation, we will look for errors or success.
            # in the finalize_automation() method, we will call the automation_success_handler() or automation_error_handler()
            # where appropriate.
            self.log_it('Checking for errors in automation')
            self.stop_automation()

            self.log_it('Finalizing automation')
            self.finalize_automation()
        except AutomationSuccessException as e:
            raise e
        except SkipAutomationException as e:
            self.automation_end_dt = datetime.now()
            raise e
        except Exception as e:
            # flag of whether or not automation has finished 'successfully'
            self.automation_error = True
            self.ok_signal.remove_signal()
            self.error_str = '[Exception] ' + str(e)
            self.error_str += OutputFormatHelper.join_output_from_list(self.error_ary)
            self.error_str += os.linesep + '------------------------ Start Traceback -------------------------' + os.linesep
            self.error_str += str(traceback.format_exc())
            self.error_str += '------------------------ End Traceback ---------------------------' + os.linesep
            self.automation_success = False
            self.automation_end_dt = datetime.now()
            self.stopped_signal.write_signal_and_data('Stopping automation due to errors at ' + str(self.automation_end_dt) + os.linesep + self.error_str)
            self.stopped_signal.append_signal_data('STOPPED|' + str(self.automation_end_dt))
            self.automation_error_handler()
            raise AutomationException('There was an error running automation ' + str(self) + ':' + os.linesep + str(self.error_str))
        finally:
            self.log_it('Removing running signal...')
            self.running_signal.remove_signal()
            self.log_it('------------------------  ENDING AUTOMATION  -------------------------------')

    def stop_automation(self):
        """
        This method will look at the self.automation_error member variable to determine if there are errors.  If so, it will write out
        the errors to the stopped signal and throw a AutomationException.
        :return: True upon success
        :rtype: bool
        """
        if self.automation_error:
            self.ok_signal.remove_signal()
            error_str = OutputFormatHelper.join_output_from_list(self.error_ary)
            self.stopped_signal.write_signal_and_data('Stopping job due to errors at ' + str(datetime.now()) + os.linesep + error_str)
            self.automation_end_dt = datetime.now()
            self.automation_success = False
            self.automation_error = True
            raise AutomationException('[STOP AUTOMATION] ' + str(self) + ':' + os.linesep + error_str)

        return True

    def clear_signals(self):
        try:
            self.log_it('Removing all *' + self.signal_extension + ' signals')
            for f in glob.glob(os.path.join(self.signal_path, "*" + self.signal_extension)):
                if self._debug:
                    self.log_it('Removing signal: ' + str(f))
                os.remove(f)
            return True
        except Exception as e:
            raise AutomationException('[EXCEPTION] running clear_signals: ' + str(e))

    def add_job(self, job):
        """
        This method adds jobs to a list.  The jobs will be executed in FIFO.
        :param job: Job instance to add to internal jobs list.
        :type job: AbstractJob
        :return: True upon success
        :rtype: bool
        """
        if not isinstance(job, AbstractJob):
            raise AutomationException('add_job requires an instance of Job')

        self.remaining_jobs_list.append(job)

        return True

    def reset_jobs(self):
        """
        This method will reset the remaining_jobs_list to an empty list
        :return: Returns True
        :rtype: bool
        """
        self.remaining_jobs_list = []
        return True

    def add_error(self, error_message):
        """
        Adds an error message to the internal errors list in order to keep track of all errors.
        :param error_message: error message to add to internal list.
        :type error_message: str
        :return: True upon success
        :rtype: bool
        """
        error_message = str(error_message).strip()
        if error_message == '':
            raise AutomationException('Error message required')
        self.error_ary.append(" " + error_message)

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

    def init_signals(self):
        """
        This method initiates all the signal objects based upon the signal files and signals that are defined here.
        """
        self.running_signal = Signal(self.signal_path, self.signal_prefix + str(self).lower() + '_running', True, self.signal_extension)
        self.ok_signal = Signal(self.signal_path, self.signal_prefix + str(self).lower() + '_ok', True, self.signal_extension)
        self.stopped_signal = Signal(self.signal_path, self.signal_prefix + str(self).lower() + '_stopped', True, self.signal_extension)
        self.dq_passed_signal = Signal(self.signal_path, self.signal_prefix + str(self).lower() + '_dq_passed', True, self.signal_extension)
        self.dq_failed_signal = Signal(self.signal_path, self.signal_prefix + str(self).lower() + '_dq_failed', True, self.signal_extension)
        self.finished_signal = Signal(self.signal_path, self.signal_prefix + str(self).lower() + '_finished', True, self.signal_extension)
        self.temp_stop_signal = Signal(self.signal_path, self.signal_prefix + str(self).lower() + '_temp_stop', True, self.signal_extension)

    def ok_to_run(self):
        """
        This method will determine if the current job is ok to run based on the current state of the signals.
        :return: True upon success
        :rtype: bool
        """

        # check signal state

        if self.temp_stop_signal.exists():
            raise SkipAutomationException('[AUTOMATION][STOPPED] ' + str(self) + ' automation temp stop is set: ' + self.temp_stop_signal.full_file_path)

        if self.global_temp_stop_signal.exists():
            raise SkipAutomationException('[AUTOMATION][STOPPED] global temp stop is set: ' + self.global_temp_stop_signal.full_file_path)

        if self.finished_signal.exists():
            self.log_it('[AUTOMATION][FINISHED] Automation finished signal is set: ' + self.finished_signal.full_file_path)
            self.log_it('[AUTOMATION][CLEARING_SIGNALS] Initializing automation')
            self.clear_signals()

        if self.stopped_signal.exists():
            raise SkipAutomationException('[AUTOMATION][ERROR] Stop signal due to error signal is set: ' + self.stopped_signal.full_file_path)

        if self.running_signal.exists():
            raise SkipAutomationException('[AUTOMATION][RUNNING] the current job is already running and the signal is set: ' + self.running_signal.full_file_path)

        return True

    def start_jobs(self):
        """
        This method is the core logic for executing and handling success / error of each individual job in the automation.
        """
        self.log_it('In start_jobs...')

        if self.total_files_to_process < 1:
            raise AutomationException('Trying to start jobs and there are no files to process!')
        try:
            # initiate the jobs
            self.init_jobs()

            # loop through the jobs and execute them
            for job in self.remaining_jobs_list:  # type: AbstractJob
                self.log_it('[' + job.job_type + '] Starting job: ' + job.get_job_name())
                try:
                    # override signal path so that the file type is included in signal path
                    job.signal_path_txt = job.job_type + '_' + job.signal_path_txt

                    # start the job
                    job.start_job()

                except JobException as e:
                    self.automation_error = True
                    self.automation_success = False
                    self.add_error('[AUTOMATION ERROR][JOB][' + job.get_job_name() + '] ' + str(e))
                    return False
                except JobSuccessException:
                    self.log_it('job ' + job.get_job_name() + ' completed successfully')
                    self.jobs_run_list.append(job)

                    # if the job is successful, should we archive the file(s)?
                    if job.job_success and job.archive_file_on_success:
                        self.log_it('Archiving file...')
                        self.archive_files()

        except Exception as e:
            self.automation_error = True
            raise AutomationException('Encountered error when processing file: ' + str(e))

    def archive_current_file(self):
        """
        This method will archive the current file and manifest.
        :return: True upon success.
        :rtype: bool
        """
        file_ret_val = self.archive_file(self.current_file_to_process)
        manifest_ret_val = self.archive_file(self.current_file_to_process)
        return file_ret_val and manifest_ret_val

    def finalize_automation(self):
        """
        This method finalizes a successful run of the automation by setting some times, writing data to signal files etc.  In addition,
        it throws the AutomationSuccessException to let automation_controller.py know that there was a successful run.
        """
        self.finished_signal.write_signal_and_data('FINISHED|' + str(datetime.now()))
        # @todo: if there are more files in the list, does the finalize_automation handle starting the automation again?
        if self.has_run_date:
            self.run_date.current_run_date_signal.write_signal_and_data('STARTED|' + str(self.automation_start_dt))
            self.run_date.current_run_date_signal.append_signal_data('COMPLETED|' + str(self.automation_end_dt))
        self.automation_end_dt = datetime.now()
        self.automation_success_handler()
        raise AutomationSuccessException('Automation has completed without errors.')

    def init_run_dates(self):
        """
        This method initiates the RunDate object should this automation rely on a run_date.
        :return: True upon success.
        :rtype: bool
        """
        if not self.has_run_date:
            return True

        self.run_date = RunDate(str(self), os.path.join(str(self), 'transaction_dates_processed'), self.run_date_format)
        self.run_date.get_current_run_date()
        self.log_it('Getting run dates...')
        self.log_it('Last Run Date: ' + str(self.run_date.last_run_date))
        self.log_it('Current Run Date: ' + str(self.run_date.current_run_date))
        return True

    def default_find_available_files(self):
        """
        This method finds all files that match the specified pattern(s)
        :return: True if all files were found or False if missing
        :rtype: bool
        """
        try:
            if len(self.filename_patterns) < 1:
                raise AutomationException('No filename patterns defined - cannot find files that match this automation.')

            ret_val = True
            for file_type, file_metadata in self.filename_patterns.iteritems():
                self.log_it('Checking for file type: ' + file_type + ' in directory ' + self.file_landing_dir)
                # check for files matching the pattern
                if self.has_run_date:
                    current_run_date = self.run_date.current_run_date_obj.strftime(file_metadata['date_pattern'])
                    if 'lag_days' in file_metadata and file_metadata['lag_days'] > 0:
                        lag_days = file_metadata['lag_days']
                        temp_file_date_obj = self.run_date.current_run_date_obj + timedelta(days=lag_days)
                        current_run_date = temp_file_date_obj.strftime(file_metadata['date_pattern'])
                        self.log_it(file_type + ' file type has ' + str(lag_days) + ' lag days.  File date should be ' + current_run_date)

                    self.log_it('File Date replacement: ' + current_run_date)
                file_pattern = file_metadata['file_pattern'].replace('{FILEDATE}', str(current_run_date))

                dir_file_pattern = os.path.join(self.file_landing_dir, file_pattern)
                found_files = sorted(glob.glob(dir_file_pattern), key=os.path.getmtime)
                num_found_files = len(found_files)
                self.log_it('[' + file_type + '] Expecting ' + str(file_metadata['num_files']) + ' file(s) for pattern ' + file_pattern + ' - found ' + str(num_found_files))
                if num_found_files != file_metadata['num_files']:
                    ret_val = False
                self.filename_patterns[file_type]['found_files'].extend(found_files)
                self.total_files_found += num_found_files

                # check for manifests matching the pattern (if defined)
                if file_metadata['manifest_pattern']:
                    manifest_pattern = file_metadata['manifest_pattern']
                    if self.has_run_date:
                        manifest_pattern = file_metadata['manifest_pattern'].replace('{FILEDATE}', str(current_run_date))

                    dir_manifest_pattern = os.path.join(self.file_landing_dir, manifest_pattern)
                    found_manifest = sorted(glob.glob(dir_manifest_pattern), key=os.path.getmtime)
                    num_found_manifests = len(found_manifest)
                    self.log_it('[' + file_type + '] Expecting ' + str(file_metadata['num_files']) + ' file(s) for pattern ' + manifest_pattern + ' - found ' + str(num_found_manifests))
                    if num_found_manifests != file_metadata['num_files']:
                        ret_val = False
                    self.filename_patterns[file_type]['found_files'].extend(found_manifest)
                    self.total_files_found += num_found_manifests

            return ret_val
        except Exception as e:
            raise AutomationException('Issue finding available files: ' + str(e))

    def get_eligible_files_for_this_run(self):
        """
        This method will get eligible files from available files (if any).
        :return: True upon success
        :rtype: bool
        """

        if len(self.error_ary) > 0:
            raise AutomationException(self.format_errors())

        try:
            for file_type, file_metadata in self.filename_patterns.iteritems():

                if len(file_metadata['found_files']) < 1:
                    raise AutomationException('No eligible files can be found as there are no available files for ' + file_type)

                for filename in file_metadata['found_files']:  # type: str
                    filename_basename = os.path.basename(filename)
                    if file_metadata['manifest_pattern']:
                        if not filename_basename.startswith(self.manifest_prefix):
                            self.log_it('Skipping file as it is not a manifest: ' + filename)
                            # check the DQ status
                            self.check_dq_status(filename, file_metadata)
                            continue
                    else:
                        # check the DQ status
                        self.check_dq_status(filename, file_metadata)

                    if self.has_run_date:
                        file_run_date_obj = self.get_run_date_of_file(filename)
                        if file_run_date_obj.strftime(self.run_date_format) != self.run_date.current_run_date_obj.strftime(self.run_date_format):
                            self.log_it('Skipping file as the run date does not match: ' + file_run_date_obj.strftime(self.run_date_format) + '!=' + self.run_date.current_run_date_obj.strftime(self.run_date_format))
                            continue
                    self.filename_patterns[file_type]['files_to_validate'].append(filename)

            if len(self.get_errors()) > 0:
                self.log_it('Automation ending due to DQ errors...')
                raise SkipAutomationException(os.linesep + self.format_errors())
            elif self.enable_dq_dependency:
                if not self.dq_passed_signal.exists():
                    self.dq_passed_signal.write_signal_and_data('All files have passed DQ.')
                self.dq_failed_signal.remove_signal()
            return True
        except SkipAutomationException as ex:
            raise ex
        except Exception as e:
            raise AutomationException('Could not get eligible files for this run: ' + str(e))

    def check_dq_status(self, filename, file_metadata):
        """
        This method will check if DQ has passed for a particular file when enabled in the file metadata.
        :param filename: This is the file to check DQ status on.
        :type filename: str
        :param file_metadata: This is the file meta data dictionary. 
        :type file_metadata: dict
        :return: True upon success, false upon failure.
        :rtype: bool
        """
        self.log_it('Checking DQ on ' + filename)
        if self.enable_dq_dependency and 'dq_signal_dir' in file_metadata and file_metadata['dq_signal_dir']:
            self.log_it('DQ enabled...')
            file_basename = os.path.basename(filename)
            dq_success_signal = Signal(file_metadata['dq_signal_dir'], file_basename, False, '_success', False)
            dq_error_signal = Signal(file_metadata['dq_signal_dir'], file_basename, False, '_error', False)

            if not dq_error_signal.exists() and not dq_success_signal.exists():
                dq_msg = '[DQ NOT RUN] ' + filename + '.  Neither of the below signals have been touched: ' + os.linesep
                dq_msg += "\t" + dq_error_signal.full_file_path
                dq_msg += os.linesep
                dq_msg += "\t" + dq_success_signal.full_file_path
                self.log_it(dq_msg)
                self.add_error(dq_msg)
                if self.dq_failed_signal.exists():
                    self.dq_failed_signal.append_signal_data(dq_msg)
                else:
                    self.dq_failed_signal.write_signal_and_data(dq_msg)
                return False
            elif dq_error_signal.exists() and not dq_error_signal.exists():
                dq_msg = '[FAILED DQ] ' + filename + os.linesep
                dq_msg += "\t" + dq_error_signal.full_file_path
                self.log_it(dq_msg)
                self.add_error(dq_msg)
                if self.dq_failed_signal.exists():
                    self.dq_failed_signal.append_signal_data(dq_msg)
                else:
                    self.dq_failed_signal.write_signal_and_data(dq_msg)
                return False
        else:
            self.log_it('DQ not enabled...')
        return True

    def get_total_automation_time(self):
        """
        This method calculates how long the automation took to complete.
        :return: Formatted string in Days, Hours, Minutes and Seconds.
        :rtype: str
        """
        time_diff = self.automation_end_dt - self.automation_start_dt
        ret_str = ''
        days, seconds = time_diff.days, time_diff.seconds
        hours = days * 24 + seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = (seconds % 60)

        include_below = False
        if days > 0:
            ret_str += '%d days' % days
            include_below = True

        if include_below or hours > 0:
            ret_str += ', ' if ret_str != '' else ''
            ret_str += '%d hours' % hours
            include_below = True

        if include_below or minutes > 0:
            ret_str += ', ' if ret_str != '' else ''
            ret_str += '%d minutes' % minutes
            include_below = True

        if include_below or seconds > 0:
            ret_str += ', ' if ret_str != '' else ''
            ret_str += '%d seconds' % seconds

        if ret_str == '':
            ret_str = '< 1 second'

        return ret_str

    def remove_stopped(self):
        """
        This method is used to remove all job and automation stopped signal files when the 'resume' command is used via
        automation_controller.py
        :return: True upon success.
        :rtype: bool
        """
        try:
            self.log_it('Removing all *_stopped*' + self.signal_extension + ' signals')
            for f in glob.glob(os.path.join(self.signal_path, "*_stopped*" + self.signal_extension)):
                if self._debug:
                    self.log_it('Removing signal: ' + str(f))
                os.remove(f)
            return True
        except Exception as e:
            raise AutomationException('[EXCEPTION] running clear_signals: ' + str(e))

    def archive_files(self):
        """
        This method will archive all files in the 'files_to_process' list.
        :return: True upon success.
        :rtype: bool
        """
        try:
            for file_type, file_metadata in self.filename_patterns.iteritems():  # type: str, dict
                num_files_to_archive = len(file_metadata['files_to_process'])
                self.log_it('Attempting to archive ' + str(num_files_to_archive) + ' files')
                if num_files_to_archive > 0:
                    for current_file in file_metadata['files_to_process']:
                        self.archive_file(current_file)

                if 'manifests_processed' in file_metadata:
                    num_manifests_to_archive = len(file_metadata['manifests_processed'])
                    self.log_it('Attempting to archive ' + str(num_manifests_to_archive) + ' manifests')
                    if num_files_to_archive > 0:
                        for current_manifest in file_metadata['manifests_processed']:
                            self.archive_file(current_manifest)
            return True
        except Exception as e:
            raise AutomationException('[ARCHIVE_FILES] ' + str(e))

    def archive_file(self, filename):
        """
        This method will archive the specified file.
        :param filename: Path to file that shoud be archived.
        :type filename: str
        :return: True upon success.
        :rtype: bool
        """

        try:
            if not filename:
                raise AutomationException('Cannot archive file(s) as there is no filename set!')

            # set the archive and filenames
            archive_dir = self.file_archive_dir
            destination_filename = os.path.basename(filename)

            # if there is a run date, let's archive the file in run-date specific folder
            if self.has_run_date:
                archive_dir = os.path.join(self.file_archive_dir, self.run_date.current_run_date)

            # create archive folder if not exists
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)

            # if the current file already exists in the archive, let's change the name so we don't overwrite it if the files differ via md5
            fev = FileExistsValidator(True)
            md5 = Md5Sum()
            archive_destination = os.path.join(archive_dir, destination_filename)
            if fev.validate(archive_destination) and not md5.compare_hash_for_files(filename, archive_destination):
                destination_filename += '_' + str(time.time())
                archive_destination = os.path.join(archive_dir, destination_filename)

            # actually move the file.  Using shutil due to symlinks
            self.log_it('Moving ' + filename + ' to ' + archive_destination)
            shutil.move(filename, archive_destination)

            return True
        except Exception as e:
            raise AutomationException('Error archiving file(s): ' + str(e))

    def __str__(self):
        """magic method when you call print({automation}) to print the name of the automation"""
        return self.__class__.__name__

    def __del__(self):
        """This is the destructor for all Automations"""
        if self.logger:
            self.logger.close_logger()
        return

    def log_name(self):
        return '_automation_'
