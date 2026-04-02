import signal
import sys
from datetime import datetime
from pydoc import locate
import os
import glob
import traceback
import random
import string
import time
import xml.etree.ElementTree as et
import csv
import shutil
import fileinput
import json

from lib.Validators import FileExistsValidator
from Toolkit.Config import AMSDependencyChecker, AMSErrorCompleteHandler, AMSSuccessCompleteHandler, AMSCompleteHandler
from Toolkit.Exceptions import AMSScheduleException, AMSDependencyCheckException, AMSCompleteHandlerException
from Toolkit.Lib import AMSReturnCode, AMSScriptReturnCode, AMSMultiThread
from Toolkit.Lib.DependencyChecks import *
from Toolkit.Lib.CompleteHandlers import *
from Toolkit.Lib.ScheduleEventHandlers import *
from Toolkit.Lib.EventHandlers import *
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from Toolkit.Lib.Signals import AMSSignal
from Toolkit.Lib.Helpers import OutputFormatHelper, AMSFile, Seconds2Time
from Toolkit.Lib.SSORun import SSORunLog
from Toolkit.Models.AMSViya import AMSViya


class AMSScheduleLauncher(AbstractAMSBase):
    def __init__(self, ams_config):
        """
        This is the init method to instantiate an AMSScheduleLauncher object.
        :param ams_config: Loaded AMSConfig object.
        :type ams_config: AMSConfig
        """

        AbstractAMSBase.__init__(self, ams_config)

        self.schedule = None  # type: str
        self.project = None  # type: str
        self.schedule_basename = None  # type: str
        self.automation_tool = None  # type:str
        self.automation_config = None  # type: str
        self.resume = None  # type: bool
        self.trigger_file = None  # type: str
        self.trigger_script = None  # type: str
        self.skip_dependencies = None  # type: bool
        self.skip_complete_handlers = None  # type: bool
        self.fev = FileExistsValidator(True)
        self.schedule_defined = False
        self.failed_dependencies = {}
        self.failed_complete_handlers = {}
        self.schedule_event_handler = AbstractAMSScheduleEventHandler.create_handler(self.AMSLogger, self.AMSConfig, None)  # type: AbstractAMSScheduleEventHandler
        self.event_handler = AbstractEventHandler.create_handler(self.AMSConfig)
        self.start_time_dt = datetime.now()
        self.complete_time = None  # datetime
        self.longtime_in_seconds = None  # int
        self.shorttime_in_seconds = None  # int
        self.AMSMultiThread = None  # type: AMSMultiThread
        self.AMSSchedule = None  # AMSSchedule
        self.schedule_shutdown_initiated = False
        self.shutdown = False
        self.sso_run_rtn_file_signal = None  # type: AMSSignal
        self.my_environment = self.AMSConfig.get_my_environment()
        self.my_logs_dir_base = None  # type: str
        self.sso_run_log_xml = None  # type: str
        self.sked_log = None # type: str
        self.jobs_in_error_dict = {}
        self.schedule_completed = False
        self.fire_error_on_exit = True
        self.created_a_ticket = False
        self.long_running_fired = False
        self.log_check_sleep_duration = 5
        self.log_check_dict = {}

    def launch_schedule(self):
        self.AMSLogger.debug('In launch_schedule for %s' % self.__whoami())
        self.AMSLogger.info('Starting schedule uuid={}'.format(self.uuid))

        # Put into the environment some cool things that can be used by scripts
        os.environ['ETL_SCHEDULE'] = self.AMSSchedule.schedule_name
        os.environ['ETL_START_TIME'] = str(self.start_time_dt)
        try:
            os.environ['ETL_JSON_SCHEDULE'] = json.dumps(self.AMSSchedule.raw_config)
        except Exception:
            self.AMSLogger.debug('No raw_config in schedule_name {}??'.format(self.AMSSchedule.schedule_name))
        try:
            os.environ['ETL_JSON_ENVIRONMENT'] = json.dumps(self.AMSConfig.raw_config['environments'])
        except Exception:
            self.AMSLogger.debug('No environments configured for schedule_name {}??'.format(self.AMSSchedule.schedule_name))

        if self.trigger_script:
            self.AMSLogger.info('Executing trigger script...')
            if FileExistsValidator.is_exe(self.trigger_script):
                try:
                    # Manually configure a dependency check for a script with only one attempt
                    config = AMSDependencyChecker()
                    config.dependency = self.trigger_script
                    config.max_attempts = 1
                    config.attempt_interval = 1
                    check = AMSScriptDependencyCheck(self.AMSConfig, config)
                    result = check.evaluate_dependency()
                    result.display_job_status()
                    if result and result.is_success():
                        self.AMSLogger.info('Successfully executed trigger script {}'.format(self.trigger_script))
                    else:
                        self.AMSLogger.info('Error executing trigger script {}'.format(self.trigger_script))
                        return
                except Exception as e:
                    self.AMSLogger.error('Error: {}'.format(str(e)))
                    self.AMSLogger.error('Problem running trigger script {} by the current user {}'.format(self.trigger_script, self.AMSDefaults.current_user))
                    return
            else:
                self.AMSLogger.info('Trigger script {} is not present or accessible by the current user {}'.format(self.trigger_script, self.AMSDefaults.current_user))
                return

        if self.trigger_file:
            self.AMSLogger.info('Checking trigger file...')
            if FileExistsValidator().validate(self.trigger_file):
                try:
                    AMSFile.clear(self.trigger_file)
                    self.AMSLogger.info('Successfully cleared trigger file {}'.format(self.trigger_file))
                except Exception as e:
                    self.AMSLogger.error('Error: {}'.format(str(e)))
                    self.AMSLogger.error('Problem clearing trigger file {} by the current user {}'.format(self.trigger_file, self.AMSDefaults.current_user))
                    return
            else:
                self.AMSLogger.info('Trigger file {} is not present or accessible by the current user {}'.format(self.trigger_file, self.AMSDefaults.current_user))
                return

        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling launch_schedule')
        else:
            self.schedule_event_handler.on_info("has launched.")

        self.AMSLogger.debug('Checking Dependencies...')
        self._check_dependencies()
        self.AMSLogger.debug('Calling before_start schedule event handler...')
        # Only trigger LLD if the event_handler_type is AMSZabbix
        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling LLD error')
        elif self.AMSConfig.ams_event_handler == 'AMSZabbix' and not self.schedule_event_handler.before_start():
            self._open_ticket_4_lld_not_run()

        if hasattr(self.AMSSchedule, 'start_stop_comment_link') and self.AMSSchedule.start_stop_comment_link:
            self._create_comment("Started Schedule: " + self.AMSSchedule.schedule_name, self.AMSSchedule.start_stop_comment_link)

        self.AMSLogger.debug('Starting Schedule...')
        self._launch_schedule()
        signal.signal(signal.SIGINT, self.stop_schedule)
        signal.signal(signal.SIGTERM, self.stop_schedule)

    def _open_ticket_4_lld_not_run(self):
        ticket_summary = self.AMSConfig.my_hostname + ' - LLD has not been run for a schedule'
        ticket_description = "LLD has failed while running a batch schedule:{}{}{}".format(self._get_schedule_name_for_description(), os.linesep, os.linesep)
        ticket_description += "This condition can occur when Zabbix is either misconfigured, the configuration file is wrong, or LLD was not run after the schedule was added.{}{}".format(os.linesep, os.linesep)
        ticket_description += "Schedule: {}{}".format(self._get_schedule_name_for_description(), os.linesep)
        ticket_description += "Full Command: {}{}".format(self._get_full_command_for_schedule(), os.linesep)
        ticket_description += "Start Time: {}{}".format(self.start_time_dt.strftime("%Y-%m-%d %H:%M:%S"), os.linesep)

        self.AMSDefaults.AMSJibbixOptions.project = self.AMSSchedule.tla
        self.AMSDefaults.AMSJibbixOptions.raw_config['project'] = self.AMSSchedule.tla
        self.create_ticket(self.AMSDefaults.AMSJibbixOptions, summary=ticket_summary, description=ticket_description, set_create=False)

    def _launch_schedule(self):
        self.AMSLogger.debug('Calling on_start schedule event handler...')
        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling on_start')
        else:
            self.schedule_event_handler.on_start()

        if self.automation_tool == 'Sked':
            self._launch_sked()
        elif self.automation_tool == 'SSORun':
            self._launch_sso_run()
        elif self.automation_tool == 'ADI':
            self._launch_adi()
        elif self.automation_tool == 'SMC':
            self._launch_smc()
        elif self.automation_tool == 'Script':
            self._launch_script()
        elif self.automation_tool == 'Job_Flow':
            self._launch_flow()
        else:
            raise AMSScheduleException('Invalid automation type given: %s' % self.automation_tool)

    def _launch_adi(self):
        self.AMSLogger.info('Launching ADI config={}'.format(self.AMSSchedule.schedule_config_file))

        # TODO: construct full path based on project homedir
        script_name = os.path.join(self.AMSSchedule.home_dir, 'bin', self.AMSDefaults.default_adi_run_path)

        # Ensure the script exists and is executable/readable
        if not FileExistsValidator.is_readable(script_name):
            raise AMSScheduleException('Script for ADI {} is not readable'.format(script_name))
        elif not FileExistsValidator.is_exe(script_name):
            raise AMSScheduleException('Script for ADI {} is not executable'.format(script_name))

        self.my_logs_dir_base = self._generate_random_dir(os.path.join(self.AMSSchedule.home_dir, 'logs'))

        self._link_path()

        self._launch_scheduler(script_name)

    def _launch_script(self):
        self.AMSLogger.info('Launching Script file={}'.format(self.AMSSchedule.schedule_name))

        # explicit path to the script is given
        self.AMSLogger.debug('Using explicit schedule as path={}'.format(self.AMSSchedule.schedule_name))
        script_name = self.AMSSchedule.schedule_name

        # Ensure the script exists and is executable/readable
        if not FileExistsValidator.is_readable(script_name):
            raise AMSScheduleException('Script for schedule {} is not readable'.format(script_name))
        elif not FileExistsValidator.is_exe(script_name):
            raise AMSScheduleException('Script for schedule {} is not executable'.format(script_name))

        self.my_logs_dir_base = self._generate_random_dir(os.path.join(self.AMSSchedule.home_dir, 'logs'))

        self._link_path()

        self._launch_scheduler(script_name)

    def _link_path(self, base_logs=None, current_path='logs/current'):
        # emulate SSORun by adding a symlink for the current job
        if base_logs is None:
            base_logs = self.my_logs_dir_base
        link_path = os.path.join(self.AMSSchedule.home_dir, current_path)
        try:
            os.remove(link_path)
        except Exception as e:
            self.AMSLogger.error('Ignoring removing symlink error={}'.format(e))
        try:
            os.symlink(base_logs, link_path)
            self.AMSLogger.info('Created symlink {} => {}'.format(current_path, base_logs))
        except Exception as e:
            self.AMSLogger.error('Problem creating symlink error={}'.format(e))

    def _launch_flow(self):
        self.AMSLogger.info('Launching Job Flow schedule: {}'.format(self.AMSSchedule.schedule_name))
        if len(self.AMSSchedule.flow_id) != 36:
            self.AMSLogger.warning('Job Flow ID may not be valid, 36 char uuid expected, got: {}'.format(self.AMSSchedule.flow_id))
        try:
            viya = AMSViya(authfile=self.AMSSchedule.flow_auth_file)
        except Exception as e:
            self.AMSLogger.error('Unable to make connection to viya instance with auth file {}'.format(
                self.AMSSchedule.flow_auth_file))
            raise e
        try:
            self.AMSLogger.debug('Searching for job definitions matching: {}'.format(self.AMSSchedule.flow_id))
            jobs = viya.list_jobs(uuid=self.AMSSchedule.flow_id)
            if len(jobs['items']) == 1:
                job = jobs['items'][0]
                if 'id' in job.keys() and job['id'] == self.AMSSchedule.flow_id:
                    self.AMSLogger.info('Launching Schedule: {}\tJob FLow Name: {}\tid: {}'.format(
                        self.AMSSchedule.schedule_name, job['name'], self.AMSSchedule.flow_id))
            else:
                raise AMSScheduleException('The schedule {} with ID {} was not found.'.format(
                    self.AMSSchedule.schedule_name, self.AMSSchedule.flow_id))
        except AMSScheduleException:
            self.AMSLogger.error('Unable to find job flow id ({}) or it does not match found list jobs ({})\n'.format(
                self.AMSSchedule.flow_id, jobs))
        except KeyError:
            self.AMSLogger.error('list_jobs did not return any job items')

        log_link = None
        try:
            job_response = viya.run_job(job_id=self.AMSSchedule.flow_id).json()
            self.AMSLogger.debug('Schedule has launched successfully, beginning polling.')
            log_link = viya.poll_job(job_response)
        except Exception as e:
            self.AMSLogger.error('Error encountered running job flow {}\n{}'.format(self.AMSSchedule.flow_id, str(e)))

        if log_link is not None:
            if viya.success == 'failed':
                self.AMSLogger.error('Running on error handlers?')
            elif viya.success == 'completed':
                self.AMSLogger.info('Running on success handlers?')

    def _launch_smc(self):
        self.AMSLogger.info('Launching SMC schedule={}'.format(self.AMSSchedule.schedule_name))

        # Handle 'RunNow' configured SMC so that the path is formed as:
        # 1. /sso/biconfig/940/Lev1/SchedulingServer/RunNow_hanrun/JBJ_Dual_Flow
        # OR
        # 2. /sso/biconfig/940/Lev1/SchedulingServer/hanrun/JBJ_Dual_Flow
        if not self.AMSSchedule.schedule_name.startswith('/'):
            # remove any trailing slashes from smc_root_dir
            if hasattr(self.AMSSchedule, 'smc_root_dir') and self.AMSSchedule.smc_root_dir:
                root_dir = os.path.abspath(self.AMSSchedule.smc_root_dir)
            else:
                root_dir = self.AMSDefaults.default_smc_path

            self.AMSLogger.debug('Finding schedule in dir={}'.format(root_dir))

            # First check to see if the smc_root_dir endswith 'RunNow'
            if root_dir.endswith('RunNow'):
                self.AMSLogger.debug('Detected RunNow configuration')
                # This is the 'RunNow' scenario
                added_path_character = '_'
            else:
                # Add the / for customized root_dirs and non-default directories
                added_path_character = '/'

            # build script_path from the AMSConfig.run_user, and schedule_name (which is flowname_identifier)
            if hasattr(self.AMSSchedule, 'flow_identifier') and self.AMSSchedule.flow_identifier:
                self.AMSLogger.debug('Using specific flow identifier of={}'.format(self.AMSSchedule.flow_identifier))
                specific_flow = "{}{}{}.sh".format(self.AMSSchedule.schedule_name, added_path_character, self.AMSSchedule.flow_identifier)
            else:
                # determine most recent flow ID
                root_loc = os.path.join(root_dir + added_path_character + self.AMSConfig.run_user, self.AMSSchedule.schedule_name, self.AMSSchedule.schedule_name+'_*.sh')
                self.AMSLogger.debug('Examining flows for flowname {} in dir={}'.format(self.AMSSchedule.schedule_name, root_loc))
                files = glob.glob(root_loc)
                self.AMSLogger.debug('Found {} potential flows: {}'.format(len(files), files))

                if not len(files):
                    raise AMSScheduleException('No flow {} found in {}'.format(self.AMSSchedule.schedule_name, root_loc))

                specific_flow = os.path.basename(max(files, key=os.path.getctime))

                self.AMSLogger.debug('Using most recent flow identifier of={}'.format(specific_flow))

            self.AMSLogger.info('Starting SMC schedule user={} flowname={} id={}'.format(self.AMSConfig.run_user, self.AMSSchedule.schedule_name, specific_flow))
            script_name = os.path.join(root_dir + added_path_character + self.AMSConfig.run_user, self.AMSSchedule.schedule_name, specific_flow)

        # Otherwise this is an absolute path given to a script to run
        else:
            self.AMSLogger.debug('Using explicit schedule as path={}'.format(self.AMSSchedule.schedule_name))
            script_name = self.AMSSchedule.schedule_name

        # Ensure the script exists and is executable/readable
        if not FileExistsValidator.is_readable(script_name):
            raise AMSScheduleException('Script for schedule {} is not readable'.format(script_name))
        elif not FileExistsValidator.is_exe(script_name):
            raise AMSScheduleException('Script for schedule {} is not executable'.format(script_name))

        self.my_logs_dir_base = os.path.dirname(script_name)

        self._link_path()

        self._launch_scheduler(script_name)

    def _launch_sked(self,max_iterations=None):
        if os.getenv('_sked_environment') is None:
            if hasattr(self.my_environment, 'env_type') and self.my_environment.env_type:
                os.environ['_sked_environment'] = str(self.my_environment.env_type)
            else:
                self.AMSLogger.debug('Environment env_type should be set for sked usage.')

        base_dir = os.path.join(self.AMSSchedule.home_dir, 'logs/sked')

        try:
            for line in fileinput.input(self.automation_config, inplace=False):
                if line.startswith("logpath="):
                    base_dir = line[len('logpath='):].strip()
                    self.AMSLogger.info('Overriding default logs directory with sked.ini logpath={}'.format(base_dir))
        except Exception as e:
            self.AMSLogger.warning('Problem overriding default logs directory error={}'.format(e))

        sked_logpath = self._generate_random_dir(base_dir)

        self._link_path(sked_logpath)

        os.environ['_sked_logpath'] = sked_logpath
        self.AMSLogger.info('Sending all sked log files to {}'.format(sked_logpath))

        self.AMSLogger.debug('Rewriting {} to comment out logpath='.format(self.automation_config))
        new_config = os.path.join(sked_logpath, 'sked.ini')
        shutil.copy(self.automation_config, new_config)
        self.automation_config = new_config

        # rewrite sked.ini to comment out the configured logpath so the environment variable '_sked_logpath' is used
        for line in fileinput.input(self.automation_config, inplace=True):
            print line.replace("logpath=", "#logpath="),

        self._launch_scheduler(self.AMSSchedule.sked_path)
        self.AMSLogger.debug("=======================================================================")
        self.sked_log = os.path.join(sked_logpath)
        self.AMSLogger.debug(self.sked_log)
        self._check_for_sked_job_errors(max_iterations)

    def _launch_sso_run(self, max_iterations=None):
        # hack to get SSORun to think you are in the correct directory:
        self.my_logs_dir_base = self._generate_random_dir(os.path.join(self.AMSSchedule.home_dir, 'logs'))
        os.environ['PWD'] = self.AMSSchedule.home_dir
        os.environ['LOGDIR'] = self.my_logs_dir_base

        # remember the sso_run log xml path for later
        self.AMSLogger.info('SSO_Run logs dir={}'.format(self.my_logs_dir_base))
        self.sso_run_log_xml = os.path.join(self.my_logs_dir_base, self.schedule_basename, 'sso_run_log.xml')
        self.AMSLogger.info('SSO_Run logfile={}'.format(self.sso_run_log_xml))

        self._launch_scheduler(self.AMSSchedule.sso_run_path)

        self._check_for_sso_run_job_errors(max_iterations)

    def _check_for_sso_run_job_errors(self, max_iterations):
        self.AMSLogger.debug('In _check_for_sso_run_job_errors.')
        self.AMSLogger.debug('checking sso_run log here: %s' % self.sso_run_log_xml)
        sleep_time = self.log_check_sleep_duration
        cntr = 0

        if self.schedule_completed:
            self.AMSLogger.warning('Schedule completed before sso_run errors could be checked!')
            return

        while not self.schedule_completed:
            if max_iterations is not None and cntr >= max_iterations:
                self.AMSLogger.info('SSO Run Log XML File has been created: %s' % self.sso_run_log_xml)
                self.AMSLogger.debug('_check_for_sso_run_job_errors returning...')
                return

            cntr += 1

            if not self.fev.validate(self.sso_run_log_xml):
                self.AMSLogger.debug('SSO Run Log XML File not yet created: %s' % self.sso_run_log_xml)
                self.AMSLogger.debug('Sleeping %s seconds...' % sleep_time)
                time.sleep(sleep_time)
                continue

            ams_return_code = self._parse_sso_run_log_xml(ignore_no_file=True)
            if self.fire_error_on_exit:
                self.AMSLogger.debug('Firing Error...')
                if self.create_ticket(self.AMSSchedule.AMSJibbixOptions, self.AMSSchedule.get_schedule_zabbix_key(), self._build_error_event_summary(), self._build_error_description(ams_return_code)):
                    self.AMSLogger.info('Created ticket checking sso_run_job_errors')
                    for job_name, job in self.jobs_in_error_dict.iteritems():
                        self.jobs_in_error_dict[job_name] = True
            self.AMSLogger.debug('Sleeping %s seconds...' % sleep_time)
            time.sleep(sleep_time)

    def _check_for_sked_job_errors(self, max_iterations):
        self.AMSLogger.debug('In _check_for_sked_job_errors.')
        self.AMSLogger.debug('checking skedlog here: %s' % self.sked_log)
        sleep_time = self.log_check_sleep_duration
        cntr = 0

        if self.schedule_completed:
            self.AMSLogger.warning('Schedule completed before sked errors could be checked!')
            return

        while not self.schedule_completed:
            if max_iterations is not None and cntr >= max_iterations:
                self.AMSLogger.debug('_check_for_sked_job_errors returning...')
                return

            cntr += 1

            if not self.fev.is_dir(self.sked_log):
                self.AMSLogger.debug('Sked Log XML File not yet created: %s' % self.sked_log)
                self.AMSLogger.debug('Sleeping %s seconds...' % sleep_time)
                time.sleep(sleep_time)
                continue

            ams_return_code = self._parse_sked_log_xml(ignore_no_file=True)
            if self.fire_error_on_exit:
                self.AMSLogger.debug('Firing Error...')
                if self.create_ticket(self.AMSSchedule.AMSJibbixOptions, self.AMSSchedule.get_schedule_zabbix_key(), self._build_error_event_summary(), self._build_error_description(ams_return_code)):
                    self.AMSLogger.info('Created ticket checking sked_job_errors')
                    for job_name, job in self.jobs_in_error_dict.iteritems():
                        self.jobs_in_error_dict[job_name] = True
            self.AMSLogger.debug('Sleeping %s seconds...' % sleep_time)
            time.sleep(sleep_time)

    def _parse_sso_run_log_xml(self, ams_return_code=None, ignore_no_file=False):
        self.AMSLogger.debug('Looking to parse sso_run log={}'.format(self.sso_run_log_xml))
        sso_run_log = SSORunLog()
        new_error_cnt = 0
        if ams_return_code is None:
            ams_return_code = AMSScriptReturnCode(os.getpid(), 1, '', '', self.sso_run_log_xml)
        try:
            sso_run_log.parse_sso_run_log(self.sso_run_log_xml)
            for job_name, job in sso_run_log.entries.iteritems():
                # send job finished if needed
                # only finished is sent for sso_run because the log is only written when a job
                # stops, not when it starts
                if job_name not in self.log_check_dict:
                    self.log_check_dict[job_name] = {'finished': True}

                    if job.is_job_error():
                        verb = 'finished (with errors)'
                    else:
                        verb = 'finished'

                    if self.schedule_event_handler:
                        self.AMSLogger.info("Sending info for Job {} has {}".format(job_name, verb))
                        self.schedule_event_handler.on_info("Job {} has {}".format(job_name, verb))
                    else:
                        # no event handler
                        pass
                else:
                    self.AMSLogger.debug("Already triggered info for Job {} has finished".format(job_name))

            if sso_run_log.error:
                for job_name, job in sso_run_log.jobs_in_error.iteritems():
                    self.AMSLogger.debug('Detected job failed: %s' % job_name)
                    ams_return_code.job_success = False
                    if job_name not in self.jobs_in_error_dict or not self.jobs_in_error_dict[job_name]:
                        new_error_cnt += 1
                        self.AMSLogger.debug('Job needs to be alerted on: %s' % job_name)
                        self.jobs_in_error_dict[job_name] = False
                        ams_return_code.failed_jobs.append(job_name)

                        ams_return_code.add_error('==================== Start Job Fail #%s ====================' % new_error_cnt)
                        try:
                            ams_return_code.add_error('Job %s Failed: %s' % (job.name, job.fullpath))
                            ams_return_code.add_error('The SSORun log path is here: %s' % job.loglink)
                            if job.file == 'controller.sh' and job.shparam:
                                lm_shparam = job.shparam.split(' ')
                                ams_return_code.add_error('Load Manager Log Location: /sso/sfw/LoadMgr/logs/%s' % lm_shparam[0])
                            ams_return_code.add_error('Customer: %s' % job.customer)
                            ams_return_code.add_error('Job Working Directory: %s' % sso_run_log.working_directory)
                            ams_return_code.add_error('Job Type: %s' % job.type)
                            ams_return_code.add_error('Job shparam: %s' % job.shparam)
                            ams_return_code.add_error('Job Elapsed Time: %s' % job.elapsed_time)
                            ams_return_code.add_error('Job Errors: %s' % job.errors)
                            ams_return_code.add_error('Job Warnings: %s' % job.warnings)
                        except:
                            pass
                        ams_return_code.add_error('==================== End Job Fail #%s ======================' % new_error_cnt)
            elif len(sso_run_log.entries) == 0:
                ams_return_code.job_success = False
                try:
                    ams_return_code.add_error('Error: No successful entries were found in sso_run_log.xml file. Please review your schedule for dependency issues and system logs for more information.')
                    ams_return_code.add_error('SSORun Log Location: %s' % self.sso_run_log_xml)
                    ams_return_code.add_error('Customer: %s' % sso_run_log.customer)
                    ams_return_code.add_error('Working Directory: %s' % sso_run_log.working_directory)
                    ams_return_code.add_error('Schedule: %s' % sso_run_log.schedule)
                except:
                    pass
            else:
                self.AMSLogger.debug('No individual job errors detected.')

            # If there have been new errors detected, ensure that fire_error_on_exit is set to True if we're
            # not doing ignore_no_file, because this means an error happened that hasn't been reported yet.
            # (btw why does this have to be SO complex!!?!?!?!)
            if ams_return_code.is_error() and not ignore_no_file:
                self.fire_error_on_exit = True
                self.AMSLogger.debug("setting fire_error_on_exit to {}".format(self.fire_error_on_exit))
            elif new_error_cnt > 0:
                self.fire_error_on_exit = True
                self.AMSLogger.debug("setting fire_error_on_exit to {}".format(self.fire_error_on_exit))
            elif new_error_cnt == 0:
                self.fire_error_on_exit = False
                self.AMSLogger.debug("setting fire_error_on_exit to {}".format(self.fire_error_on_exit))
        except Exception as E:
            self.AMSLogger.error("Unhandled Exception parsing sso_run log: %s" % str(E))
            self.AMSLogger.error(traceback.format_exc())
            ams_return_code.add_error('Error: Problem parsing sso_run_log.xml file. Please review cron and system logs for more information.')
            ams_return_code.add_error('SSORun Log Location: %s' % self.sso_run_log_xml)
            ams_return_code.add_error('Unhandled Exception: %s' % str(E))
            ams_return_code.job_success = False

        return ams_return_code

    def _parse_smc_log(self, ams_return_code=None):
        if ams_return_code is None:
            ams_return_code = AMSScriptReturnCode(os.getpid(), 1, '', '', self.my_logs_dir_base)

        # list files in dir

        # if schedule is an absolute path, then make logs base off of the script name
        if self.AMSSchedule.schedule_name.startswith('/'):
            logsdir = os.path.dirname(self.AMSSchedule.schedule_name)
            files = glob.glob(str(self.AMSSchedule.schedule_name).replace('.sh', '_*.log'))
        # otherwise look in the SAS logs directory based off of the flowname
        else:
            logsdir = self.AMSDefaults.default_sas_logs
            files = glob.glob(os.path.join(self.AMSDefaults.default_sas_logs,self.AMSSchedule.schedule_name+'_*.log'))
        # sort by creation time and reverse them so the first is the most recent
        files = sorted(files, key=os.path.getctime)
        files.reverse()
        ams_return_code.add_error('')
        ams_return_code.add_error('Flow {} Failed!'.format(self.AMSSchedule.schedule_name))
        ams_return_code.add_error('')
        ams_return_code.add_error('Please check the logfiles in {}'.format(logsdir))
        ams_return_code.add_error('')
        for f in files:
            ts = datetime.fromtimestamp(os.stat(f).st_ctime)
            self.AMSLogger.debug('Comparing datetimes {} to {}'.format(ts, self.start_time_dt))
            if ts > self.start_time_dt:
                self.AMSLogger.debug('Searching file {} for errors'.format(f))
                with open(f) as logfile:
                    try:
                        if 'ERROR:' in logfile.read():
                            ams_return_code.failed_jobs.append(os.path.basename(f))
                            ams_return_code.add_error('ERRORs are found in {}'.format(f))
                    except:
                        self.AMSLogger.debug('No errors found in file {}'.format(f))
                        pass
            else:
                # No more log files to search
                self.AMSLogger.debug('Stopped searching file list as {} is before start of schedule'.format(f))
                break

        return ams_return_code

    def _parse_sked_log_xml(self, ams_return_code=None,ignore_no_file=False):
        if ams_return_code is None:
            ams_return_code = AMSScriptReturnCode(os.getpid(), 1, '', '', self.my_logs_dir_base)

        # list file in dir
        files = glob.glob(os.path.join(self.my_logs_dir_base,'*.log.psv'))
        # read each psv as a Sked log file -- realistically there is only one because we'd created the logs directory
        new_error_cnt = 0

        if len(files) == 0:
            self.AMSLogger.debug('No log.psv files found?')

        for f in files:
            self.AMSLogger.debug('Parsing sked log file={}'.format(f))
            with open(f) as csvfile:
                reader = csv.reader(csvfile, delimiter="|")
                try:
                    # skip header row
                    self.AMSLogger.debug('Skipping header row={}'.format(next(reader)))
                except:
                    pass

                for row in reader:
                    self.AMSLogger.debug('Examining sked log row={}'.format(row))
                    try:
                        if row[1] == 'Job' and (row[3] == 'Starting' or row[3] == 'Finished' or row[3] == 'Error'):
                            # if not in dictionary
                            if row[5] not in self.log_check_dict:
                                self.log_check_dict[row[5]] = {'started': False, 'finished': False}

                            trigger = False
                            verb = ''
                            if row[3] == 'Finished' and not self.log_check_dict[row[5]]['finished']:
                                self.log_check_dict[row[5]]['finished']= True
                                trigger = True
                                verb = 'finished'
                            elif row[3] == 'Error' and not self.log_check_dict[row[5]]['finished']:
                                self.log_check_dict[row[5]]['finished'] = True
                                trigger = True
                                verb = 'finished (with errors)'
                            elif not self.log_check_dict[row[5]]['started']:
                                self.log_check_dict[row[5]]['started'] = True
                                trigger = True
                                verb = 'started'
                            if self.schedule_event_handler:
                                if trigger:
                                    self.AMSLogger.info("Sending info for Job {} has {}".format(row[5], verb))
                                    self.schedule_event_handler.on_info("Job {} has {}".format(row[5], verb))
                                else:
                                    self.AMSLogger.debug("Already triggered info for Job {} has {}".format(row[5], verb))

                        if row[3] == 'Error':
                            self.AMSLogger.debug('Parsing sked log detected Error in row={}'.format(row))
                            # when any Error is found, then ensure then schedule fails regardless of it being a Job, or Schedule error
                            # this will ensure we catch all errors regardless of how they occur
                            # also, we can't trust the exit code from sked, so if there is any error set the returncode to 1
                            ams_return_code.job_success = False
                            ams_return_code.returncode = 1

                            # Only add Job errors to the ams_return_code
                            if row[1] == 'Job':
                                if row[5] not in self.log_check_dict:
                                    self.log_check_dict[row[5]] = {'started': False, 'finished': True}
                                    trigger = True

                                if self.schedule_event_handler:
                                    if trigger:
                                        self.AMSLogger.info("Sending info for Job {} has finished (with Errors)".format(row[5]))
                                        self.schedule_event_handler.on_info("Job {} has finished (with Errors)".format(row[5]))
                                    else:
                                        self.AMSLogger.debug(
                                            "Already triggered info for Job {} has has finished (with Errors)".format(row[5]))

                                trigger = False
                                date_time = row[0]
                                fullrunfile = row[4]
                                name_alias = row[5]
                                if name_alias+'('+fullrunfile+')' not in self.jobs_in_error_dict or not self.jobs_in_error_dict[name_alias+'('+fullrunfile+')']:
                                    ams_return_code.failed_jobs.append(name_alias+'('+fullrunfile+')')
                                    new_error_cnt += 1
                                    self.jobs_in_error_dict[name_alias+'('+fullrunfile+')'] = False
                                    ams_return_code.add_error('==================== Start Job Fail #%s ====================' % new_error_cnt)
                                    ams_return_code.add_error('Job %s Failed: %s' % (name_alias, fullrunfile))
                                    ams_return_code.add_error('Job Date Time: %s' % date_time)
                                    ams_return_code.add_error('Sked log path: %s' % self.my_logs_dir_base)
                                    ams_return_code.add_error('==================== End Job Fail #%s ======================' % new_error_cnt)
                    except Exception as e:
                        self.AMSLogger.error('Problem parsing row={} exception={}'.format(row, e))

        if ams_return_code.is_error() and not ignore_no_file:
            self.fire_error_on_exit = True
            self.AMSLogger.debug("setting fire_error_on_exit to {}".format(self.fire_error_on_exit))
        elif new_error_cnt > 0:
            self.fire_error_on_exit = True
            self.AMSLogger.debug("setting fire_error_on_exit to {}".format(self.fire_error_on_exit))
        elif new_error_cnt == 0:
            self.fire_error_on_exit = False
            self.AMSLogger.debug("setting fire_error_on_exit to {}".format(self.fire_error_on_exit))

        return ams_return_code

    def _parse_script_log(self, ams_return_code=None):
        if ams_return_code is None:
            ams_return_code = AMSScriptReturnCode(os.getpid(), 0, '', '', self.my_logs_dir_base)

        # list file in dir
        files = glob.glob(os.path.join(self.my_logs_dir_base ,'*.log'))
        # read each log file7
        for f in files:
            with open(f) as logfile:
                self.AMSLogger.debug('Examining logfile log ={}'.format(f))
                try:
                    if 'ERROR:' in logfile.read():
                        ams_return_code.add_error('Schedule {} failed.'.format(self.AMSSchedule.schedule_name))
                        ams_return_code.add_error('Script log path is here: {}'.format(self.my_logs_dir_base))
                        ams_return_code.add_error('ERRORs are found in {}'.format(f))
                    else:
                        ams_return_code.add_message('No errors are found in {}'.format(f))
                        self.AMSLogger.debug('No errors found in file {}'.format(f))
                except:
                    self.AMSLogger.debug('Exceptions occurred while reading file {}'.format(f))
                    pass
        return ams_return_code

    def _launch_scheduler(self, tool):
        run_args = []

        if self.AMSSchedule.automation_type in ('SSORun', 'Sked'):
            run_args = ['-c', self.automation_config, '-s', self.schedule]

            # For SSORun, Sked, and ADI we always run 'from the beginning' unless resume is specified
            if not self.resume:
                run_args.append('-f')

        if self.AMSSchedule.automation_type in ('ADI'):
            run_args = ['-c', self.automation_config]

            # For ADI, rerun from previous run if resume is specified otherwise always run from the beginning
            if self.resume:
                run_args.append('-r')
            else:
                run_args.append('-f')

            # apply debug arg if specified
            if self.AMSConfig.debug:
                run_args.append('-d')

        # To ensure that SMC launched scripts always skip the atq rescheduling always launch with 'now'
        if self.AMSSchedule.automation_type in ('SMC'):
            run_args = ['now']

        # this needs to be forked into a new thread
        self.AMSMultiThread = AMSMultiThread(self.AMSConfig, max_workers=self.AMSConfig.multi_thread_max_workers, timer_interval=self.AMSConfig.multi_thread_timer_check_interval)

        # @todo: figure out how to pass in jibbix_options from self.AMSSchedule.AMSJibbixOptions
        self.AMSMultiThread.run_job(tool, jibbix_options=None, group_name=self.schedule, command_line_args=run_args,
                                    callback_method=self._complete_handler,
                                    long_running_callback=self._long_running_handler, cwd=self.AMSSchedule.home_dir,
                                    long_running_seconds=self._get_longtime_to_pass_to_script_runner(),
                                    schedule=self.AMSSchedule, ams_config=self.AMSConfig)

    def _long_running_handler(self):
        self.AMSLogger.info('In _longrunning_handler....')
        longtime_jibbix = self.AMSSchedule.AMSJibbixOptions
        # if there is a defined longtime_jibbix_options then use it
        if self.AMSSchedule.AMSLongtimeJibbixOptions is not None:
            self.AMSLogger.info('Overriding longtime jibbix options with {}'.format(self.AMSSchedule.AMSLongtimeJibbixOptions))
            longtime_jibbix = self.AMSSchedule.AMSLongtimeJibbixOptions
        if self.AMSSchedule.longtime_priority:
            self.AMSLogger.info('Overriding longtime priority of {} with {}'.format(self.AMSSchedule.AMSJibbixOptions.priority, self.AMSSchedule.longtime_priority))
            longtime_jibbix.priority = self.AMSSchedule.longtime_priority
        self.create_ticket(longtime_jibbix, self.AMSSchedule.get_schedule_zabbix_key(), self.build_long_running_event_summary(), self.build_long_or_short_running_description(), set_create=False)
        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling on_long_running')
        else:
            self.schedule_event_handler.on_long_running()
        self.long_running_fired = True
        return True

    def _get_longtime_to_pass_to_script_runner(self):
        return self.longtime_in_seconds

    def _short_running_handler(self):
        self.AMSLogger.info('In _shortrunning_handler....')
        self.create_ticket(self.AMSSchedule.AMSJibbixOptions, self.AMSSchedule.get_schedule_zabbix_key(), self.build_short_running_event_summary(), self.build_long_or_short_running_description(False), set_create=False)
        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling on_short_running')
        else:
            self.schedule_event_handler.on_short_running()
        return True

    def _complete_handler(self, ams_return_code):
        """

        :param ams_return_code:
        :type ams_return_code: AMSScriptReturnCode
        :return:
        :rtype:
        """
        self.schedule_completed = True
        self.complete_time = datetime.now()

        ams_return_code.display_job_status()
        if self.automation_tool == 'SSORun':
            # Let's get the number of failed jobs:
            num_sso_run_errors = self._is_sso_run_error()
            if num_sso_run_errors > 0:
                self.AMSLogger.info('Signal file {} indicated that sso_run failed.'.format(self.sso_run_rtn_file_signal))

                if ams_return_code.is_success():
                    self.AMSLogger.warning('Return code of exec''ing sso_run was {} but signal file indicated it failed.'.format(ams_return_code.get_returncode()))

                ams_return_code.job_success = False

            if self.fev.validate(self.sso_run_log_xml):
                self.AMSLogger.debug('SSO Run Log XML File exists: %s' % self.sso_run_log_xml)
                ams_return_code = self._parse_sso_run_log_xml(ams_return_code)
            else:
                self.AMSLogger.debug('SSO Run Log XML File does not exist: %s' % self.sso_run_log_xml)
            # Undoing hack for SSORun
            os.environ['PWD'] = os.getcwd()

        elif self.automation_tool == 'Sked':
            if self.fev.directory_readable(self.my_logs_dir_base):
                self.AMSLogger.debug('Sked Log Directory exists: %s' % self.my_logs_dir_base)
                ams_return_code = self._parse_sked_log_xml(ams_return_code)
            else:
                self.AMSLogger.debug('SSO Run Log Directory does not exist: %s' % self.my_logs_dir_base)

        # Parse SAS Logs if SMC schedule fails
        elif self.automation_tool == 'SMC':
            if ams_return_code.returncode == 1:
                ams_return_code.job_success = True
                self.AMSLogger.warning('SMC schedule has finished with warnings. This is not cool, but it is what it is.')
            elif ams_return_code.is_error():
                self.AMSLogger.debug('Parsing SMC logs...')
                ams_return_code = self._parse_smc_log(ams_return_code)
            else:
                # SMC job success
                pass

        elif self.automation_tool in('Script', 'ADI'):
            self.AMSLogger.debug('{} finished with ADI'.format(self.automation_tool))
            # write stdout and stderr to logs directory
            self.AMSLogger.info('Writing completed log files to {}'.format(self.my_logs_dir_base))
            with open(os.path.join(self.my_logs_dir_base, self.schedule_basename + ".log"), "w") as rc_file:
                rc_file.write(ams_return_code.get_message())
            with open(os.path.join(self.my_logs_dir_base, self.schedule_basename + "_out.log"), "w") as stdout_file:
                stdout_file.write(ams_return_code.std_out)
            with open(os.path.join(self.my_logs_dir_base, self.schedule_basename + "_err.log"), "w") as stderr_file:
                stderr_file.write(ams_return_code.std_err)

        else:
            # Other scheduler??
            raise AMSScheduleException('Invalid automation type given: %s' % self.automation_tool)

        self.AMSLogger.debug('Calling on_finish schedule event handler...')
        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling on_finish')
        else:
            self.schedule_event_handler.on_finish()

        finish = (self.complete_time - self.start_time_dt).seconds
        if finish < self.shorttime_in_seconds:
            self._short_running_handler()
            # If the short time triggers, then the schedule is in error
            ams_return_code.job_success = False

        if self.AMSSchedule.schedule_update_comment_link or self.AMSSchedule.start_stop_comment_link:
            self.AMSLogger.debug('Adding Log Run Stats...')
            self._run_log_run_stats(ams_return_code)
        else:
            self.AMSLogger.debug('Log Run Stats are not enabled')

        self.AMSLogger.debug('ams_return_code.is_error(): %s' % ams_return_code.is_error())

        if ams_return_code.is_error():
            self._run_error_handler(ams_return_code, self.skip_complete_handlers)

        self.AMSLogger.debug('Calling after_finish schedule event handler...')
        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling after_finish')
        else:
            self.schedule_event_handler.after_finish()

        # Create ticket merged to previous long_running ticket
        if self.long_running_fired:
            self.AMSLogger.info('Generating longtime completion ticket')
            longtime_jibbix = self.AMSSchedule.AMSJibbixOptions
            if self.AMSSchedule.longtime_priority:
                self.AMSLogger.info('Overriding longtime priority of {} with {}'.format(self.AMSSchedule.AMSJibbixOptions.priority, self.AMSSchedule.longtime_priority))
                longtime_jibbix.priority = self.AMSSchedule.longtime_priority
            longtime_jibbix.merge = 'yes'
            self.event_handler.create(options=longtime_jibbix, schedule=None,
                                      summary=self.build_long_running_event_summary(),
                                      description=self.build_long_or_short_running_description(job_success=ams_return_code.is_success()))

        if ams_return_code.is_error():
            self.AMSLogger.debug('AMSReturnCode showed an error occurred. Exiting.')
            self.shutdown_gracefully()
            sys.exit(1)

        self.AMSLogger.debug('Calling success handler(s)...')
        if not self.skip_complete_handlers:
            self._run_success_handler()
        else:
            self.AMSLogger.info('Skipping success complete handlers')

        self.shutdown_gracefully()
        sys.exit(0)

    def _run_error_handler(self, ams_return_code, skip_complete_handlers):
        if not skip_complete_handlers:
            self.AMSLogger.debug('Calling on_error schedule event handler...')
            if not self.schedule_event_handler:
                self.AMSLogger.warning('No schedule_event_handler is defined for calling on_error')
            else:
                self.schedule_event_handler.on_error()
        else:
            self.AMSLogger.info('Skipping error complete handlers')

        # Use Defaults if Schedule options are None
        if self.AMSSchedule.AMSJibbixOptions is None:
            options = self.AMSDefaults.AMSJibbixOptions
        else:
            options = self.AMSSchedule.AMSJibbixOptions

        if self.fire_error_on_exit:
            self.create_ticket(options, self.AMSSchedule.get_schedule_zabbix_key(), self._build_error_event_summary(), self._build_error_description(ams_return_code))

        if not skip_complete_handlers:
            try:
                self.AMSLogger.debug('Calling AMSErrorCompleteHandlers...')
                if len(self.AMSSchedule.AMSErrorCompleteHandler) > 0:
                    for complete_handler_name, complete_handler_config in self.AMSSchedule.AMSErrorCompleteHandler.iteritems():  # type: str, AMSErrorCompleteHandler
                        self._run_complete_handler(complete_handler_config, False)

                if len(self.failed_complete_handlers) > 0:
                    self._throw_failed_complete_handlers('error')
            except AMSCompleteHandlerException:
                pass
            except Exception as E:
                ams_return_code.add_error("Unhandled Exception: %s" % str(E))

    def _run_success_handler(self):
        try:
            if len(self.AMSSchedule.AMSSuccessCompleteHandler) > 0:
                for complete_handler_name, complete_handler_config in self.AMSSchedule.AMSSuccessCompleteHandler.iteritems():  # type: str, AMSSuccessCompleteHandler
                    self._run_complete_handler(complete_handler_config, True)

                if len(self.failed_complete_handlers) > 0:
                    self._throw_failed_complete_handlers('success')
        except AMSCompleteHandlerException:
            pass
        except Exception as E:
            self.AMSLogger.error("Unhandled Exception: %s" % str(E))
            self.AMSLogger.error(traceback.format_exc())

    def _run_log_run_stats(self, ams_return_code):
        try:
            if ams_return_code.is_error():
                zbx_text = "Completed schedule (with errors): " + self.AMSSchedule.schedule_name
            else:
                zbx_text = "Completed schedule successfully: " + self.AMSSchedule.schedule_name

            # Try to reduce # of separate tickets created
            if self.AMSSchedule.start_stop_comment_link:
                if not self.AMSSchedule.schedule_update_comment_link:
                    # Only start_stop is configured so create and return
                    comment_text = zbx_text + os.linesep + 'Total Runtime: ' + self._get_total_automation_time()

                    self._create_comment(comment_text, self.AMSSchedule.start_stop_comment_link)
                    return
                elif self.AMSSchedule.schedule_update_comment_link != self.AMSSchedule.start_stop_comment_link:
                    # if only the start/stop is configured or start/stop and the detailed stats are different then add the comment for start/stop separately
                    # with the internally calculated Total Time -- this isn't reading from the ssorun/sked logs as we aren't parsing stats
                    comment_text = zbx_text + os.linesep + 'Total Runtime: ' + self._get_total_automation_time()

                    self._create_comment(comment_text, self.AMSSchedule.start_stop_comment_link)

            if self.AMSSchedule.automation_type == 'SSORun':
                self.AMSLogger.info('Parsing log file %s' % self.sso_run_log_xml)

                tree = et.parse(self.sso_run_log_xml)
                root = tree.getroot()

                elapsed_text = ''

                elapsed = None
                sso_log_text = ''
                for child in root.findall('entry'):
                    sso_log_text += '{}{}'.format(child.get('name'), os.linesep)
                    sso_log_text += 'Status: {}{}'.format(child.get('status'), os.linesep)
                    sso_log_text += 'Elapsed Time: {}{}'.format(child.get('elapsed'), os.linesep)
                    sso_log_text += 'Start Time: {}{}'.format(child.get('start_time'), os.linesep)
                    sso_log_text += 'End Time: {}{}'.format(child.get('end_time'), os.linesep)
                    sso_log_text += os.linesep
                    elapsed = child.get('elapsed_time')

                # Remember the last elapsed time for the total runtime
                if elapsed:
                    elapsed_text += '{}{}: {}{}{}'.format(os.linesep, "Total Runtime", elapsed, os.linesep, os.linesep)

                run_log_text = os.linesep + "Run Log: {}".format(self.sso_run_log_xml)

                zbx_text += elapsed_text + sso_log_text + run_log_text

            elif self.AMSSchedule.automation_type == 'Sked':
                # For now, let's add in the runtime calculated internally, later we'll add more
                # details as we parse the sked log files
                zbx_text += os.linesep + 'Total Runtime: ' + self._get_total_automation_time()

            self._create_comment(zbx_text, self.AMSSchedule.schedule_update_comment_link)

        except Exception as E:
            self.AMSLogger.error("Unhandled Exception: %s" % str(E))
            self.AMSLogger.error(traceback.format_exc())

    def _create_comment(self, text, link):
        try:
            # Do jibbix stuff here
            add_comment_jibbix_options = locate('Toolkit.Config.AMSJibbixOptions')()  # type: AMSJibbixOptions
            add_comment_jibbix_options.comment_only = 'true'
            add_comment_jibbix_options.link = link
            add_comment_jibbix_options.project = self.AMSSchedule.AMSJibbixOptions.project
            add_comment_jibbix_options.summary = 'No Summary (comment only)'
            add_comment_jibbix_options.description = "{}:{}{}".format(self.AMSConfig.get_my_environment().env_type, os.linesep, os.linesep)
            add_comment_jibbix_options.description += "{}{}".format(text, os.linesep)

            # Invoke the event handler with None as the schedule name so that the default toolkit.options zabbix item is used
            self.create_ticket(add_comment_jibbix_options, set_create=False)
        except Exception as E:
            self.AMSLogger.error("Unhandled Exception: %s" % str(E))
            self.AMSLogger.error(traceback.format_exc())

    def _run_complete_handler(self, complete_handler_config, is_success):
        complete_handler_tmp = 'AMS' + complete_handler_config.type + 'CompleteHandler'

        self.AMSLogger.info("Running {} complete handler".format(complete_handler_config.type))

        # Ensure there is a valid complete handler
        if complete_handler_tmp in globals():
            complete_handler_obj = globals()[complete_handler_tmp](self.AMSConfig, complete_handler_config)  # type: AbstractCompleteHandler
            # I apologize for hacking this in ... perhaps a 'job info' object would be better
            self.AMSSchedule.sso_run_log_xml = self.sso_run_log_xml
            complete_handler_res = complete_handler_obj.evaluate_complete_handler(self.AMSSchedule, is_success)
            complete_handler_res.display_job_status()

            if not complete_handler_res.is_success():
                self.failed_complete_handlers[complete_handler_config.complete_handler_name] = {
                    'config': complete_handler_config,
                    'object': complete_handler_obj,
                    'result': complete_handler_res
                }
                self.AMSLogger.debug('{} Complete Handler was not successful.'.format(complete_handler_config.type))
                return False
            else:
                self.AMSLogger.debug('Successfully launched Complete Handler {}.'.format(complete_handler_config.type))
        else:
            self.AMSLogger.debug('Complete Handler(s) %s do not exist.' % complete_handler_config.type)
            return False

        return True

    def create_ticket(self, options, key=None, summary=None, description=None, set_create=True):
        uuid_text = '{}uuid={}'.format(os.linesep, self.uuid)

        if description:
            description += uuid_text
        elif options.description:
            options.description += uuid_text
        else:
            description = uuid_text

        if self.created_a_ticket and set_create and options:
            self.AMSLogger.info('Merging this ticket into previous ticket if possible')
            options.merge = 'Yes'

        result = self.event_handler.create(options, key, summary, description)
        if result and set_create:
            self.created_a_ticket = True
            self.AMSLogger.info('Ticket was created, so future ticket creations will merge if possible')

        return result

    def _throw_failed_complete_handlers(self, handler_type):
        self.complete_time = datetime.now()
        exception_str = ''
        for complete_handler_name, complete_handler_dict in self.failed_complete_handlers.iteritems():  # type: str, dict
            if exception_str:
                exception_str += os.linesep
            complete_handler_config = complete_handler_dict['config']  # type: AMSCompleteHandler
            complete_handler_obj = complete_handler_dict['object']  # type: AbstractCompleteHandler
            complete_handler_res = complete_handler_dict['result']  # type: AMSReturnCode
            exception_str += 'Complete Handler(s) %s[%s] failed: %s%s%s' % (
                complete_handler_name, complete_handler_config.type, complete_handler_config.complete_handler,
                os.linesep,
                os.linesep)

            if complete_handler_config.details:
                exception_str += '{}{}{}'.format(complete_handler_config.details, os.linesep, os.linesep)
            if complete_handler_config.runbook_sub_link:
                exception_str += 'Complete Handler Runbook Link: {}{}{}'.format(complete_handler_config.runbook_sub_link, os.linesep, os.linesep)

            exception_str += complete_handler_obj.instructions_for_verification()

            # Append errors if any exist
            if complete_handler_res.is_error():
                exception_str += '%s%sErrors follow:%s%s' % (os.linesep, os.linesep, os.linesep, complete_handler_res.format_errors())

        if handler_type == 'error':
            ticket_summary = self._build_complete_error_handler_event_summary()
        else:
            ticket_summary = self._build_complete_success_handler_event_summary()

        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling on_batch_delay')
        else:
            self.schedule_event_handler.on_batch_delay()
        self.AMSLogger.debug('Failed Complete Handler: Cut ticket.')
        self.create_ticket(self.AMSSchedule.AMSJibbixOptions, self.AMSSchedule.get_schedule_zabbix_key(), ticket_summary, self._build_complete_handler_failure_description(exception_str, handler_type))
        raise AMSCompleteHandlerException(exception_str)

    def _is_sso_run_error(self):
        self.sso_run_rtn_file_signal = AMSSignal(os.path.join(self.AMSSchedule.home_dir, 'run'), self.schedule_basename, True, '.xml.rtn')
        self.AMSLogger.debug('Signal File object dump:%s %s' % (os.linesep, str(self.sso_run_rtn_file_signal)))
        if self.sso_run_rtn_file_signal.signal_data is None:
            self.AMSLogger.debug('Signal File data is empty - signal file does not already exist!')
            return 0
        error_array = self.sso_run_rtn_file_signal.signal_data.split(os.linesep)
        self.AMSLogger.info('Number of jobs SSORun failed with errors: %s' % int(error_array[0]))
        self.AMSLogger.info('Number of jobs SSORun success with warnings: %s' % int(error_array[1]))
        return int(error_array[0])

    def _build_error_event_summary(self):
        return "%s | Batch schedule failed: %s" % (self.AMSConfig.my_hostname, self._get_schedule_name_for_description())

    def _build_error_description(self, ams_return_code):
        """

        :param ams_return_code:
        :type ams_return_code: AMSScriptReturnCode
        :return:
        :rtype:
        """
        if self.complete_time is None:
            description = "Batch schedule {} is still running, but one or more jobs has failed.{}".format(self._get_short_schedule_name_for_description(), os.linesep)
            description += "This condition can occur when jobs run in parallel or there are not dependencies on subsequent jobs in the schedule.{}{}".format(os.linesep, os.linesep)
        else:
            description = "Batch schedule {} has failed.{}{}".format(self._get_short_schedule_name_for_description(), os.linesep, os.linesep)
        description += "Schedule: %s%s" % (self._get_schedule_name_for_description(), os.linesep)
        if ams_return_code.get_failed_jobs():
            description += "Jobs Failed: %s%s" % (ams_return_code.format_failed_jobs(), os.linesep)
        description += "Logs Directory: %s%s" % (self.my_logs_dir_base, os.linesep)
        description += "Error Code(s): %s%s" % (ams_return_code.get_returncode(), os.linesep)
        description += "Start Time: %s%s" % (self.start_time_dt.strftime("%Y-%m-%d %H:%M:%S"), os.linesep)
        if self.complete_time is None:
            description += "Completed Time: Schedule is still running, but one of the jobs has failed.%s" % os.linesep
        else:
            description += "Completed Time: %s%s" % (self.complete_time.strftime("%Y-%m-%d %H:%M:%S"), os.linesep)
        description += "Run Time: %s%s" % (self._get_total_automation_time(), os.linesep)
        description += os.linesep
        description += "Full Command: %s%s" % (self._get_full_command_for_schedule(), os.linesep)
        description += "Error: %s%s" % (ams_return_code.format_errors(), os.linesep)
        description = self._get_extra_details(description)
        description = self._add_runbook_link(description)
        return description

    def build_long_running_event_summary(self):
        make_readable = Seconds2Time(sec=self.longtime_in_seconds)
        return "%s | Batch schedule long running (%s): %s " % (self.AMSConfig.my_hostname, make_readable.convert2readable(), self._get_schedule_name_for_description())

    def build_short_running_event_summary(self):
        make_readable = Seconds2Time(sec=self.shorttime_in_seconds)
        return "%s | Batch schedule short running (%s): %s " % (self.AMSConfig.my_hostname, make_readable.convert2readable(), self._get_schedule_name_for_description())

    def _get_short_schedule_name_for_description(self):
        if not self.AMSSchedule:
            name = None
        elif self.AMSSchedule.schedule_name == self.schedule:
            name = self.AMSSchedule.schedule_name
        else:
            name = self.schedule
        if name:
            return os.path.basename(name)
        else:
            return 'None'

    def _get_schedule_name_for_description(self):
        if self.AMSSchedule.schedule_name == self.schedule:
            return "{}::{}".format(self.AMSSchedule.project_name, self.AMSSchedule.schedule_name)

        # if the schedule_name and the schedule are not the same then this is an adhoc schedule run
        # so ensure the ticket created shows the adhoc schedule name also
        return '{} - {}::{}'.format(self.AMSSchedule.schedule_name, self.AMSSchedule.project_name, self.schedule)

    def build_long_or_short_running_description(self, is_long=True, job_success=False):
        make_readable_long = Seconds2Time(sec=self.longtime_in_seconds)
        make_readable_short = Seconds2Time(sec=self.shorttime_in_seconds)
        num_asterisks = 10
        if self.complete_time:
            description = "%sUPDATE%s%sThe schedule has completed %s%s%sPlease close this ticket as appropriate%s%s" % (num_asterisks*'*', num_asterisks*'*', os.linesep, 'successfully' if job_success else 'with errors', os.linesep, os.linesep, os.linesep, os.linesep)
        else:
            description = "The schedule execution time has passed the %s running threshold of %s%s%sAn update to this ticket will automatically occur when the schedule completes%s%sIf the schedule does not complete in a reasonable amount of time it is still running so please investigate%s%s" % (
                ('long' if is_long else 'short'), (make_readable_long.convert2readable() if is_long else make_readable_short.convert2readable()), os.linesep, os.linesep, os.linesep, os.linesep, os.linesep, os.linesep)
        description += "Schedule: %s%s" % (self._get_schedule_name_for_description(), os.linesep)
        description += "Full Command: %s%s" % (self._get_full_command_for_schedule(), os.linesep)
        description += "Start Time: %s%s" % (self.start_time_dt.strftime("%Y-%m-%d %H:%M:%S"), os.linesep)
        description += "%s" % ("Current Run Time: " if not self.complete_time else "Total Run Time: ")
        description += "%s%s" % (self._get_total_automation_time(), os.linesep)
        description = self._get_extra_details(description)
        description = self._add_runbook_link(description)

        return description

    def _get_extra_details(self, description):
        if not self.AMSSchedule.details:
            return description

        description += os.linesep
        description += "Extra Details: %s%s" % (self.AMSSchedule.details, os.linesep)
        return description

    def _add_runbook_link(self, description):
        runbook_link = self.AMSConfig.get_runbook_link_for_schedule(self.AMSSchedule.schedule_name)
        if not runbook_link:
            return description

        description += os.linesep
        description += "Runbook Link: %s%s" % (runbook_link, os.linesep)

        return description

    def _get_total_automation_time(self):
        """
        Method now calls utility class that returns the same result
        This method calculates how long the automation took to complete.
        :return: Formatted string in Days, Hours, Minutes and Seconds.
        :rtype: str
        """

        if self.complete_time is None:
            time_diff = datetime.now() - self.start_time_dt
        else:
            time_diff = self.complete_time - self.start_time_dt

        make_readable = Seconds2Time(sec=time_diff.total_seconds())
        return make_readable.convert2readable()

    def validate_args(self, args):
        self.AMSLogger.debug('Validating Arguments...')
        if hasattr(args, 'config_file'):
            self.AMSLogger.debug('config_file={}'.format(args.config_file))
        if hasattr(args, 'schedule'):
            self.AMSLogger.debug('schedule={}'.format(args.schedule))
        if hasattr(args, 'adhoc_schedule'):
            self.AMSLogger.debug('adhoc_schedule={}'.format(args.adhoc_schedule))
        if hasattr(args, 'resume'):
            self.AMSLogger.debug('resume={}'.format(args.resume))
        if hasattr(args, 'trigger_file'):
            self.AMSLogger.debug('trigger_file={}'.format(args.trigger_file))
        if hasattr(args, 'trigger_script'):
            self.AMSLogger.debug('trigger_script={}'.format(args.trigger_script))
        if hasattr(args, 'longtime'):
            self.AMSLogger.debug('longtime={}'.format(args.longtime))
        if hasattr(args, 'shorttime'):
            self.AMSLogger.debug('shorttime={}'.format(args.shorttime))
        if hasattr(args, 'skip_dependencies'):
            self.AMSLogger.debug('skip_dependencies={}'.format(args.skip_dependencies))
        if hasattr(args, 'skip_complete_handlers'):
            self.AMSLogger.debug('skip_complete_handlers={}'.format(args.skip_complete_handlers))
        if hasattr(args, 'project'):
            self.AMSLogger.debug('project={}'.format(args.project))

        if hasattr(args, 'schedule') and args.schedule:
            self.schedule = str(args.schedule).strip()
        if hasattr(args, 'project') and args.project:
            self.project = str(args.project).strip()
        if hasattr(args, 'adhoc_schedule') and args.adhoc_schedule:
            adhoc_schedule = str(args.adhoc_schedule).strip()
        else:
            adhoc_schedule = None
        if hasattr(args, 'resume') and args.resume:
            self.resume = args.resume
        else:
            self.resume = False
        if hasattr(args, 'trigger_file') and args.trigger_file:
            self.trigger_file = args.trigger_file
        if hasattr(args, 'trigger_script') and args.trigger_script:
            self.trigger_script = args.trigger_script
        if hasattr(args, 'longtime') and args.longtime:
            self.longtime_in_seconds = args.longtime
        if hasattr(args, 'shorttime') and args.shorttime:
            self.shorttime_in_seconds = args.shorttime
        if hasattr(args, 'skip_dependencies') and args.skip_dependencies:
            self.skip_dependencies = args.skip_dependencies
        if hasattr(args, 'skip_complete_handlers') and args.skip_complete_handlers:
            self.skip_complete_handlers = args.skip_complete_handlers

        if self.longtime_in_seconds == -1:
            self.longtime_in_seconds = None
        elif self.longtime_in_seconds < 0:
            self.fev.add_error('--longtime', 'Must be >= 0')

        if self.shorttime_in_seconds == -1:
            self.shorttime_in_seconds = None
        elif self.shorttime_in_seconds < 0:
            self.fev.add_error('--shorttime', 'Must be >= 0')

        if not self.schedule or len(self.schedule) == 0:
            self.fev.add_error('--schedule', 'Argument required')
        else:
            self.schedule_basename = os.path.basename(self.schedule)

        self.AMSLogger.debug('Lookup schedule in config file...')
        if not self._get_schedule_from_config():
            self.fev.add_error('--schedule', 'Schedule %s does not exist in config file' % self.schedule)
        else:
            self.AMSLogger.debug('Found schedule in config file...')

        if adhoc_schedule is not None:
            if not self.fev.validate(adhoc_schedule):
                self.fev.add_error('--adhoc_schedule', 'Adhoc schedule file %s does not exist' % adhoc_schedule)
            else:
                self.schedule = adhoc_schedule
                self.schedule_basename = os.path.basename(adhoc_schedule)

        # update the schedule in the handler
        if self.schedule_event_handler:
            self.schedule_event_handler.set_schedule(self.schedule)

        if not self.automation_config and self.AMSSchedule and self.AMSSchedule.automation_type in ('SSORun', 'Sked') and not self.AMSSchedule.schedule_config_file:
            self.fev.add_error('automation_config',
                               'No automation config has been specified via the AMS Toolkit config file.')

        if not isinstance(self.resume, bool):
            self.fev.add_error('--resume', 'Requires boolean True or False')

        if len(self.fev.get_errors()) > 0:
            raise AMSScheduleException(self.fev.format_errors())

    def _get_schedule_from_config(self):

        try:
            self.AMSSchedule = self.AMSConfig.get_schedule_by_name(self.schedule, self.project)
            self.schedule_defined = True
            self.automation_config = self.AMSSchedule.schedule_config_file
            self.automation_tool = self.AMSSchedule.automation_type
            if self.longtime_in_seconds is None and self.AMSSchedule.longtime > 0:
                self.AMSLogger.info('Setting longtime from config to %s seconds' % self.AMSSchedule.longtime)
                self.longtime_in_seconds = self.AMSSchedule.longtime
            if self.shorttime_in_seconds is None and self.AMSSchedule.shorttime > 0:
                self.AMSLogger.info('Setting shorttime from config to %s seconds' % self.AMSSchedule.shorttime)
                self.shorttime_in_seconds = self.AMSSchedule.shorttime

            return True
        except AMSScheduleException:
            self.AMSLogger.debug(
                'Could not find a schedule defined in config with the given name %s.  Going to use the default, ad-hoc schedule...' % self.schedule)
            return False

    def _check_dependencies(self):
        result = None
        if len(self.AMSSchedule.AMSDependencyChecks) > 0 and not self.skip_dependencies:
            self.AMSLogger.debug('Calling on_dependency schedule event handler...')
            if not self.schedule_event_handler:
                self.AMSLogger.warning('No schedule_event_handler is defined for calling on_dependency')
            else:
                self.schedule_event_handler.on_info("is checking {} dependencies policy='{}'".format(len(self.AMSSchedule.AMSDependencyChecks), self.AMSSchedule.dependency_check_policy))

            if hasattr(self.AMSSchedule, 'start_stop_comment_link') and self.AMSSchedule.start_stop_comment_link:
                self._create_comment("Checking Dependencies: " + self.AMSSchedule.schedule_name, self.AMSSchedule.start_stop_comment_link)

            for dependency_check_name, ams_dependency_check_config in self.AMSSchedule.AMSDependencyChecks.iteritems():  # type: str, AMSDependencyChecker
                self.AMSLogger.debug('Checking dependency: {}'.format(dependency_check_name))
                self.schedule_event_handler.on_dependency("{}[{}]".format(dependency_check_name, ams_dependency_check_config.type))
                dependency = self._check_dependency(ams_dependency_check_config)
                if dependency:
                    dependency.display_job_status()
                    if not result:
                        result = dependency
                    else:
                        result.add_result(dependency)

                    if result.is_error():
                        self.schedule_event_handler.on_info("Dependency {}[{}] failed".format(dependency_check_name, ams_dependency_check_config.type))
                    else:
                        self.schedule_event_handler.on_info("Dependency {}[{}] succeeded".format(dependency_check_name, ams_dependency_check_config.type))

                    # Be sure to check the result of this specific dependency check for evaluating the fail first policy
                    if dependency.is_error() and self.AMSSchedule.dependency_check_policy == self.AMSDefaults.available_dependency_check_policies[0]:
                        self.AMSLogger.info("Stopping dependency check after first discovered failure")
                        break

        if len(self.failed_dependencies) > 0:
            self.AMSLogger.info('dependencies failed')

            some_text = '\n'
            for dependency_name, dependency_dict in self.failed_dependencies.iteritems():  # type: str, dict
                ams_return_code = dependency_dict['result']  # type: AMSReturnCode
                ams_dependency_check_config = dependency_dict['config']  # type: AMSDependencyChecker
                some_text += 'Dependency %s[%s] failed: %s%s' % (
                            dependency_name, ams_dependency_check_config.type, ams_return_code.get_message(), os.linesep)
                if isinstance(ams_return_code, AMSScriptReturnCode) and len(ams_return_code.std_err):
                    some_text += '{}'.format(ams_return_code.std_err)
            self.schedule_event_handler.on_info(some_text)
            self.schedule_event_handler.on_info("dependencies failed")

            text = ''
            if hasattr(self.AMSSchedule, 'start_stop_comment_link') and self.AMSSchedule.start_stop_comment_link:
                text = "Dependencies Failed: " + self.AMSSchedule.schedule_name

            if hasattr(self.AMSSchedule, 'schedule_update_comment_link') and self.AMSSchedule.schedule_update_comment_link and hasattr(self.AMSSchedule, 'start_stop_comment_link') and self.AMSSchedule.start_stop_comment_link:
                exception_str = ''
                for dependency_name, dependency_dict in self.failed_dependencies.iteritems():  # type: str, dict
                    try:
                        ams_dependency_check_config = dependency_dict['config']  # type: AMSDependencyChecker
                        exception_str += 'Dependency %s[%s] failed: %s%s' % (
                            dependency_name, ams_dependency_check_config.type, ams_dependency_check_config.dependency, os.linesep)
                    except:
                        pass
                if text:
                    text += os.linesep
                text += exception_str

                if text:
                    self._create_comment(text, self.AMSSchedule.start_stop_comment_link)

            self._throw_failed_dependencies(result)
        else:
            if len(self.AMSSchedule.AMSDependencyChecks):
                self.AMSLogger.info('dependencies succeeded')
                self.schedule_event_handler.on_info("dependencies succeeded")

            if hasattr(self.AMSSchedule, 'start_stop_comment_link') and self.AMSSchedule.start_stop_comment_link:
                self._create_comment("Dependencies Successful: " + self.AMSSchedule.schedule_name, self.AMSSchedule.start_stop_comment_link)
            else:
                self.AMSLogger.info('No dependencies are configured')

            return True

    def _check_dependency(self, ams_dependency_check_config):
        """
        This method will fire off a dependency check in a separate thread and monitor the results
        :param ams_dependency_check_config: Dependency check config
        :type ams_dependency_check_config: AMSDependencyChecker
        :return: True upon success, false on failure
        :rtype: AMSReturnCode
        """
        self.AMSLogger.debug('In __check_dependency for %s' % ams_dependency_check_config.dependency_check_name)
        dependency_tmp = 'AMS' + ams_dependency_check_config.type + 'DependencyCheck'
        dependency_check_obj = globals()[dependency_tmp](self.AMSConfig,
                                                         ams_dependency_check_config)  # type: AbstractAMSDependencyCheck
        dependency_res = dependency_check_obj.evaluate_dependency()
        if not dependency_res.is_success():
            dependency_res.message = dependency_check_obj.commandline_output()
            self.failed_dependencies[ams_dependency_check_config.dependency_check_name] = {
                'config': ams_dependency_check_config,
                'object': dependency_check_obj,
                'result': dependency_res
            }
            return dependency_res

        return dependency_res

    def _throw_failed_dependencies(self, result):
        self.complete_time = datetime.now()
        exception_str = ''
        for dependency_name, dependency_dict in self.failed_dependencies.iteritems():  # type: str, dict
            if exception_str:
                exception_str += os.linesep

            ams_dependency_check_config = dependency_dict['config']  # type: AMSDependencyChecker
            dependency_check_obj = dependency_dict['object']  # type: AbstractAMSDependencyCheck
            exception_str += 'Dependency %s[%s] failed: %s%s%s' % (
                dependency_name, ams_dependency_check_config.type, ams_dependency_check_config.dependency, os.linesep,
                os.linesep)

            if ams_dependency_check_config.details:
                exception_str += '{}{}{}'.format(ams_dependency_check_config.details, os.linesep, os.linesep)
            if ams_dependency_check_config.runbook_sub_link:
                exception_str += 'Dependency Runbook Link: {}{}{}'.format(ams_dependency_check_config.runbook_sub_link, os.linesep, os.linesep)

            exception_str += dependency_check_obj.instructions_for_verification()

        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling on_batch_delay')
        else:
            self.schedule_event_handler.on_batch_delay()
            dependency_jibbix = self.AMSSchedule.AMSJibbixOptions
            if self.AMSSchedule.AMSDependencyJibbixOptions is not None:
                dependency_jibbix = self.AMSSchedule.AMSDependencyJibbixOptions
            self.create_ticket(dependency_jibbix, self.AMSSchedule.get_schedule_zabbix_key(),
                                      self._build_batch_delay_event_summary(),
                                      self._build_batch_delay_description(exception_str, result))

        raise AMSDependencyCheckException(exception_str)

    def _build_complete_error_handler_event_summary(self):
        return '%s | Schedule has failed and also failed to run at least one Error Handler | %s' % (self.AMSConfig.my_hostname, self._get_schedule_name_for_description())

    def _build_complete_success_handler_event_summary(self):
        return '%s | Schedule has completed successfully but failed to run at least one Success Handler | %s' % (self.AMSConfig.my_hostname, self._get_schedule_name_for_description())

    def _build_complete_handler_failure_description(self, error_str, handler_type):
        if self.AMSSchedule.AMSJibbixOptions.comment_only and self.AMSSchedule.AMSJibbixOptions.comment_only == 'yes':
            return self.AMSSchedule.AMSJibbixOptions.comment

        if handler_type == 'error':
            object_type = 'Error Handler'
        else:
            object_type = 'Success Handler'
        description = "Batch has failed one or more %s.  Please investigate%s%s" % (object_type, os.linesep, os.linesep)
        description += error_str + os.linesep
        description = self._get_extra_details(description)
        description = self._add_runbook_link(description)

        return description

    def _build_batch_delay_event_summary(self):
        return '%s | %s Schedule has failed at least one dependency check | Batch Delay' % (self.AMSConfig.my_hostname, self._get_schedule_name_for_description())

    def _build_batch_delay_description(self, error_str, result):
        description = "Batch has failed %s dependencies.  Please investigate.%s%s" % (
            len(self.failed_dependencies), os.linesep, os.linesep)
        description += error_str + os.linesep + os.linesep
        if result:
            description += result.format_errors() + os.linesep + os.linesep
        description += "Start Time: %s%s" % (self.start_time_dt.strftime("%Y-%m-%d %H:%M:%S"), os.linesep)
        description += "Run Time: %s%s" % (self._get_total_automation_time(), os.linesep)
        description += "Incoming Directory: %s" % self.AMSConfig.get_incoming_directory_by_schedule_name(self.AMSSchedule.schedule_name)
        description = self._get_extra_details(description)
        description = self._add_runbook_link(description)

        return description

    def end_schedule(self):
        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling end_schedule')
        else:
            if not self.complete_time:
                self.AMSLogger.info('The schedule has ended (no schedule started).')
                if self.trigger_script or self.trigger_file:
                    # don't do anything here. we don't want to update zabbix in this case
                    pass
                else:
                    # only add 'info' if a schedule was
                    self.schedule_event_handler.on_info("has ended (no schedule started).")
            else:
                self.AMSLogger.info('The schedule has ended.')
                self.schedule_event_handler.on_info("has ended.")

    def stop_schedule(self, signum=None, frame=None, raised_exception=None):
        self.AMSLogger.info('Stopping schedule uuid={}'.format(self.uuid))

        self.AMSLogger.info("[%s] Shutting down schedule and exiting..." % signum)
        self.complete_time = datetime.now()
        if not self.schedule_event_handler:
            self.AMSLogger.warning('No schedule_event_handler is defined for calling stop_schedule')
        else:
            self.schedule_event_handler.on_error()
        if self.AMSSchedule is not None:
            # Use Default options if not set on Schedule
            if self.AMSSchedule.AMSJibbixOptions is None:
                options = self.AMSDefaults.AMSJibbixOptions
            else:
                options = self.AMSSchedule.AMSJibbixOptions
            self.create_ticket(options, self.AMSSchedule.get_schedule_zabbix_key(),
                                      self._build_killed_event_summary(),
                                      self._build_batch_killed_description(raised_exception, signum))
        else:
            ticket_description = 'Please investigate the schedule launched on the following host as it failed before it could get any information from the desired schedule.  This schedule did not run on: ' + self.AMSConfig.my_hostname
            if raised_exception:
                ticket_description = self._build_batch_killed_description(raised_exception, signum)
            self.create_ticket(self.AMSDefaults.AMSJibbixOptions, summary=self.AMSConfig.my_hostname + ' - unknown schedule failed to launch.', description=ticket_description)
        if not self.schedule_shutdown_initiated and self.AMSMultiThread is not None:
            self.schedule_shutdown_initiated = True
            self.AMSLogger.debug(
                'User has cancelled script with sig interrupt or sigterm.  Killing program after schedule was launched..killing threads...')
            self.AMSMultiThread.shutdown(wait=False)
            sys.exit(1)
        else:
            self.AMSLogger.debug(
                'User has cancelled script with sig interrupt or sigterm.  Killing program before schedule was launched, likely still in dependency checks...')
            sys.exit(1)

    def _build_killed_event_summary(self):
        return "%s | Batch schedule killed: %s " % (self.AMSConfig.my_hostname, self._get_schedule_name_for_description())

    def _build_batch_killed_description(self, raised_exception=None, signum=None):

        if signum and signum in (signal.SIGTERM, signal.SIGKILL):
            description = "Batch schedule {} has failed to complete successfully or it was killed.{}{}".format(self._get_short_schedule_name_for_description(), os.linesep, os.linesep)
        else:
            description = "Batch schedule {} has failed.{}{}".format(self._get_short_schedule_name_for_description(), os.linesep, os.linesep)

        if raised_exception and isinstance(raised_exception, Exception):
            description += "Exception:{}{}{}".format(os.linesep, str(raised_exception), os.linesep)

        if self.AMSSchedule:
            description += "Schedule: %s%s" % (self._get_schedule_name_for_description(), os.linesep)
        description += "Full Command: %s%s" % (self._get_full_command_for_schedule(), os.linesep)
        description += "Start Time: %s%s" % (self.start_time_dt.strftime("%Y-%m-%d %H:%M:%S"), os.linesep)
        description += "Completed Time: %s%s" % (self.complete_time.strftime("%Y-%m-%d %H:%M:%S"), os.linesep)
        description += "Run Time: %s%s" % (self._get_total_automation_time(), os.linesep)

        if self.AMSSchedule:
            description = self._get_extra_details(description)
            description = self._add_runbook_link(description)

        return description

    def shutdown_gracefully(self):
        if self.AMSMultiThread is not None:
            self.AMSLogger.debug('shutdown_gracefully initiate')
            self.AMSMultiThread.shutdown()

    @staticmethod
    def _get_full_command_for_schedule():
        return OutputFormatHelper.join_output_from_list(sys.argv, ' ')

    def _generate_random_dir(self, log_dir, num_chars=16, num_iterations=100):
        if not isinstance(num_chars, int):
            raise AMSScheduleException('Invalid input for num_chars - needs to be an int')
        valid_dir = False
        cnt = 0
        cur_date = datetime.today().strftime('%Y%m%d')
        cur_time = datetime.now().strftime('%H%M%S')
        while not valid_dir:
            if cnt >= num_iterations:
                raise AMSScheduleException('Could not create a new directory for logging')
            new_dir = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(num_chars))
            new_dir_time = cur_time + '_' + new_dir
            self.my_logs_dir_base = os.path.join(log_dir, cur_date, new_dir_time)
            if not self.fev.directory_exists(self.my_logs_dir_base):
                valid_dir = True
                os.makedirs(self.my_logs_dir_base)

            cnt += 1

        self.AMSLogger.debug('Generated random directory: %s' % self.my_logs_dir_base)

        return self.my_logs_dir_base

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

    def __del__(self):
        self.shutdown_gracefully()
