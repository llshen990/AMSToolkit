import os
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from datetime import timedelta

from Automation import AbstractAutomation
from lib.Job.Jobs import Shell
from lib.Exceptions import AutomationException
from lib.Helpers import FileGetTransDate, SASEmail, AutomationErrorAutoJiraHelper, Text2Html, DecryptPgP
from lib.Validators import ManifestValidator

class USDReport(AbstractAutomation):
    """
    This class houses the USD automation.  To add jobs, modify the init_jobs method.
    """

    def __init__(self, debug):
        AbstractAutomation.__init__(self)
        # set debug
        self._debug = True if debug == True else False
        self.has_run_date = True

        if not self.config.has_option('DEFAULT', 'ssoaid_bin_dir'):
            raise AutomationException('ssoaid bin directory is not defined.')

        if not self.config.has_option('DEFAULT', 'decrypt_script'):
            raise AutomationException('decrypt_script is not defined.')

        self.decrypt_script_path = self.config.get('DEFAULT', 'decrypt_script')
        self.ssoaid_bin_dir = self.config.get('DEFAULT', 'ssoaid_bin_dir')

        if self.config.has_option('DEFAULT', 'dq_enable_auto_jira'):
            self.dq_enable_auto_jira = self.config.getboolean('DEFAULT', 'dq_enable_auto_jira')
        else:
            self.dq_enable_auto_jira = False

        self.auto_jira_fail_obj = AutomationErrorAutoJiraHelper()
        if self.config.has_option('DEFAULT', 'automation_error_assignee'):
            self.auto_jira_fail_obj.assignee = self.config.get('DEFAULT', 'automation_error_assignee')

        if self.config.has_option('DEFAULT', 'automation_error_priority'):
            self.auto_jira_fail_obj.priority = self.config.get('DEFAULT', 'automation_error_priority')

        self.decrypter = None  # type: DecryptPgP

    def set_filename_patterns(self):
        """
        This method sets the file patterns for this batch as well as metadata associated with any found files.
        :return: True
        :rtype: True
        """
        self.filename_patterns = {
            'mx_wc_usd': {
                'dq_signal_dir': self.dq_signal_dir,
                'lag_days': 5,
                'file_pattern': 'file.*.mex.mx_wc.mx_wc_usd_{FILEDATE}.txt.pgp',
                'date_pattern': '%m_%d_%Y',
                'manifest_pattern': 'manifest.*.mex.mx_wc.mx_wc_usd_{FILEDATE}.txt.pgp',
                'num_files': 1,
                'found_files': [],
                'files_to_validate': [],
                'files_to_process': [],
                'manifests_processed': []
            },
            'mx_wm_usd': {
                'dq_signal_dir': self.dq_signal_dir,
                'lag_days': 5,
                'file_pattern': 'file.*.mex.mx_wm.mx_wm_usd_{FILEDATE}.txt.pgp',
                'date_pattern': '%m_%d_%Y',
                'manifest_pattern': 'manifest.*.mex.mx_wm.mx_wm_usd_{FILEDATE}.txt.pgp',
                'num_files': 1,
                'found_files': [],
                'files_to_validate': [],
                'files_to_process': [],
                'manifests_processed': []
            }
        }

        return True

    def init_jobs(self):
        """
        This will be the main functionality of the USD Report automation.  This will determine what
        jobs to run and in what order.
        :return: Will return True upon success.
        :rtype: bool
        """
        self.reset_jobs()

        # this will add jobs to extract all USD report files into the appropriate extract tables.
        for file_type, file_metadata in self.filename_patterns.iteritems():  # type: str, dict
            for current_file in file_metadata['files_to_process']:
                self.log_it('[' + file_type + '] Initiating jobs for file: ' + current_file)

                # set the current file to process
                self.current_file_to_process = current_file

                # set the current manifest that's processing
                self.current_manifest_to_process = None
                if file_metadata['manifest_pattern']:
                    self.current_manifest_to_process = self.current_file_to_process.replace(self.file_prefix, self.manifest_prefix, 1)

                # decrypt the file.
                self.decrypter = DecryptPgP(self.current_file_to_process, self.decrypt_script_path)
                self.decrypter.shred_on_del = False

                script = os.path.abspath(os.path.join(self.ssoaid_bin_dir, 'sso_custom_extract_single_file.sh'))
                job = Shell(script, self.signal_path, self._debug)
                job.add_attribute('-f')
                job.add_attribute(self.decrypter.decrypted_file_path)
                job.signal_path_txt = 'sso_custom_extract_single_file'
                job.job_type = file_type
                self.add_job(job)

        # this job will combine all extracted data into the USDREPORTDATA extract table.
        script = os.path.abspath(os.path.join(self.ssoaid_bin_dir, 'extract_usdreportdata_automation.sh'))
        job = Shell(script, self.signal_path, self._debug)
        job.signal_path_txt = 'extract_usdreportdata'
        job.job_type = 'extract_usdreportdata'
        self.add_job(job)

        # This job will run AML job 48
        script = os.path.abspath(os.path.join(self.ssoaid_bin_dir, '..', '..', 'bat', 'runAMLJob.sh'))
        job = Shell(script, self.signal_path, self._debug)
        job.add_attribute('48')
        job.signal_path_txt = 'fscRunAMLJob_48'
        job.job_type = 'fscRunAMLJob[48]'
        self.add_job(job)

        # This job will run AML job 19
        script = os.path.abspath(os.path.join(self.ssoaid_bin_dir, '..', '..', 'bat', 'runAMLJob.sh'))
        job = Shell(script, self.signal_path, self._debug)
        job.add_attribute('19')
        job.signal_path_txt = 'fscRunAMLJob_19'
        job.job_type = 'fscRunAMLJob[19]'
        self.add_job(job)

        self.log_it('Current day of the week: ' + self.run_date.current_run_date_obj.strftime('%a'))
        if self.run_date.current_run_date_obj.strftime('%a') == 'Fri':
            self.log_it('Running USD report generation')
            begin_report_date_obj = self.run_date.current_run_date_obj - timedelta(days=6)
            begin_report_date_str = begin_report_date_obj.strftime('%d%b%Y')
            end_report_date_str = self.run_date.current_run_date_obj.strftime('%d%b%Y')
            script = os.path.abspath(os.path.join(self.ssoaid_bin_dir, '..', '..', 'bat', 'runDataLoad.sh'))
            job = Shell(script, self.signal_path, self._debug)
            job.add_attribute('-u')
            job.add_attribute(begin_report_date_str + '-' + end_report_date_str)
            job.signal_path_txt = 'runDataLoad_usd_' + begin_report_date_str + '_' + end_report_date_str
            job.job_type = 'usd_report_generation'
            self.add_job(job)

        return True

    def get_run_date_of_file(self, filename):
        """
        This method will get the transaction date of the file from the filename.
        :return: Run date in %Y%m%d format
        :rtype: string
        """

        file_get_date = FileGetTransDate()
        return file_get_date.get_trans_date_from_filename(filename)

    def find_available_files(self):
        """
        This method finds all files that match the specified pattern(s)
        :return: True if all files were found or False if missing
        :rtype: bool
        """
        return self.default_find_available_files()

    def validate_eligible_fies(self):
        """
        This method will validate that files are eligible by checking the manifest file against the corresponding found files.
        :return: True upon success
        :rtype: bool
        """
        for file_type, file_metadata in self.filename_patterns.iteritems():
            if len(file_metadata['files_to_validate']) < 1:
                raise AutomationException('No eligible files to process')

            # noinspection PyTypeChecker
            for filename in file_metadata['files_to_validate']:
                manifest_validator = ManifestValidator()
                if not manifest_validator.validate(filename, filename.replace(self.manifest_prefix, self.file_prefix, 1)):
                    raise AutomationException('Could not validate manifest / file combo: ' + os.linesep + 'File: ' + manifest_validator.file + os.linesep + 'Manifest: ' + manifest_validator.manifest + os.linesep + 'Errors: ' + os.linesep + manifest_validator.format_errors())

                # noinspection PyTypeChecker,PyUnresolvedReferences
                self.filename_patterns[file_type]['files_to_process'].append(manifest_validator.file)
                # noinspection PyTypeChecker,PyUnresolvedReferences
                self.filename_patterns[file_type]['manifests_processed'].append(manifest_validator.manifest)
                self.total_files_to_process += 1

        return True

    def automation_start_handler(self):
        """
        This method is a start handler to take action(s) when an automation starts.
        :return: True upon success
        :rtype: bool
        """
        if self.automation_email_list:
            self.log_it('Sending automation start email to: ' + self.automation_email_list)
            sas_email = SASEmail()
            sas_email.set_from('replies-disabled@sas.com')
            sas_email.set_to(self.automation_email_list)
            sas_email.set_subject("[AUTOMATION][" + str(self) + "] Start - " + str(self.automation_start_dt))
            email_msg = 'Automation has started for ' + str(self) + '.'
            email_msg += '<br /><br />Logs can be found here: ' + self.logger.log_file
            email_msg += '<br />Signals can be found here: ' + self.signal_path
            email_msg += '<br /><br />'
            email_msg += 'Thank you,<br />'
            email_msg += 'Team SSOD'
            sas_email.set_text_message(email_msg)
            sas_email.send()
        else:
            self.log_it('In automation_start_handler - no "automation_email_list" set in config.')

        return True

    def automation_success_handler(self):
        """
        This method is a success handler for a successful automation run.
        :return: True upon success.
        :rtype: bool
        """
        try:
            self.log_it('Archiving file...')
            self.archive_files()

            if self.automation_email_list:
                self.log_it('Sending automation success email to: ' + self.automation_email_list)
                sas_email = SASEmail()
                sas_email.set_from('replies-disabled@sas.com')
                sas_email.set_to(self.automation_email_list)
                sas_email.set_subject("[AUTOMATION][" + str(self) + "] Success - " + str(self.automation_end_dt))
                email_msg = 'Hello,<br /><br />We have successfully completed the ' + str(self)
                email_msg += ' automation for run date ' + str(self.run_date.current_run_date) + '.  The automation took ' + self.get_total_automation_time() + ' to complete.'
                email_msg += '<br /><br />Logs can be found here: ' + self.logger.log_file
                email_msg += '<br />Signals can be found here: ' + self.signal_path
                email_msg += '<br /><br />'
                email_msg += 'Thank you,<br />'
                email_msg += 'Team SSOD'
                sas_email.set_text_message(email_msg)
                sas_email.send()
                print email_msg
            else:
                self.log_it('In automation_success_handler - no "automation_email_list" set in config.')
        except Exception as e:
            msg = 'Caught error in automation_success_handler: ' + str(e)
            self.log_it(msg)
            self.add_error(msg)
            self.error_str += os.linesep + msg

    def automation_error_handler(self):
        """
        This method is a error handler to take action(s) upon errors.
        :return: True upon success.
        :rtype: bool
        """
        try:
            if self.automation_email_list:
                self.log_it('Sending automation error email to: ' + self.automation_email_list)
                sas_email = SASEmail()
                sas_email.set_from('replies-disabled@sas.com')
                sas_email.set_to(self.automation_email_list)
                sas_email.set_subject("[AUTOMATION][" + str(self) + "] Error - Transaction Date: " + str(self.run_date.current_run_date))
                # sas_email.set_text_message('Hello Team,' + os.linesep + 'We encountered an error running this automation.  Please see below for details: ' + os.linesep + os.linesep + self.error_str)
                email_msg = 'Hello,<br /><br />We encountered an error running the ' + str(self)
                email_msg += ' automation for run date ' + str(self.run_date.current_run_date) + '.  The automation took ' + str(self.get_total_automation_time()) + ' to complete.'
                email_msg += '<br />Logs can be found here: ' + self.logger.log_file
                email_msg += '<br />Signals can be found here: ' + self.signal_path
                email_msg += '<br />Please see below for details: <br />'
                t2h = Text2Html(self.error_str)
                email_msg += t2h.nl2br(True)
                email_msg += '<br />'
                email_msg += 'Thank you,<br />'
                email_msg += 'Team SSOD'
                sas_email.set_text_message(email_msg)
                sas_email.send()
            else:
                self.log_it('In automation_error_handler - no "automation_email_list" set in config.')
        except Exception as e:
            msg = 'Caught error in automation_error_handler while trying to send email: ' + str(e)
            self.log_it(msg)
            self.add_error(msg)
            self.error_str += os.linesep + msg

        try:
            if self.auto_jira_fail_obj and self.dq_enable_auto_jira:
                self.log_it('Sending automation auto Jira for error')
                summary = str(self) + ' | ' + "Transaction Date: " + str(self.run_date.current_run_date)
                if self.current_file_to_process:
                    summary += ' - ' + self.current_file_to_process
                self.auto_jira_fail_obj.set_parameters(summary, self.error_str)
                self.auto_jira_fail_obj.send_zabbix_message()
            else:
                self.log_it('In automation_error_handler - no "auto_jira_fail_obj" set in config or it is disabled.')
        except Exception as e:
            msg = 'Caught error in automation_error_handler trying auto jira: ' + str(e)
            self.log_it(msg)
            self.add_error(msg)
            self.error_str += os.linesep + msg

        return True