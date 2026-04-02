import logging
import socket
import sys
import re
import os
import getpass
import subprocess

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.MetaClasses import Singleton

class AMSDefaults(object):
    __metaclass__ = Singleton

    """
    This function is here to support unit testing so we can mock this function.
    """
    @staticmethod
    def get_app_path():
        return APP_PATH

    """
    This class defines several default config values for AMS monitoring
    """
    def __init__(self):
        self.debug = False  # type: bool
        self.config_version = 1
        self.email_address = 'ssoretailops@wnt.sas.com'  # type: str
        self.from_address = 'replies-disabled@sas.com'  # type: str
        self.max_mail_subject_length = 78  # type: int
        self.incoming_dir = '/sso/transport/incoming'  # type: str
        self.outgoing_dir = '/sso/transport/outgoing'  # type: str
        self.archive_dir = '/sso/transport/archive'  # type: str
        self.event_handler = 'AMSZabbix'  # type: str
        self.zabbix_url = 'https://status.ondemand.sas.com/zabbix/'  # type: str
        self.zabbix_proxy = 'zabproxy.vsp.sas.com'  # type: str
        self.zabbix_config_file = '/etc/zabbix/zabbix_agentd.conf'  # type: str
        self.zabbix_template_name = 'AMS Batch Monitoring LLD - GHUSPS'  # type: str
        self.zabbix_web_template_name = 'AMS Web Scenario LLD - GHUSPS'  # type: str
        self.zabbix_hostgroup_name = 'AMS Batch Monitored Hosts'  # type: str
        self.zabbix_batch_monitoring_lld_key = 'ams_batch_monitoring_ghusps.lld'
        self.zabbix_file_route_lld_key = 'ams_file_route_ghusps.lld'
        self.zabbix_stp_web_health_check_lld_key = 'ams_stp_web_health_check_ghusps.lld'
        self.zabbix_ams_web_scenario_lld_key = 'ams_web_scenario_ghusps.lld'
        self.zabbix_setup_iterations_to_wait = 30
        self.zabbix_setup_iteration_duration = 60
        self.zabbix_clear_proxy_config_cache_command = '/usr/sbin/zabbix_proxy -R config_cache_reload'
        self.zabbix_clear_proxy_config_cache_hostname = 'zabix03au.vsp.sas.com'
        self.zabbix_clear_proxy_config_cache_retries = 3
        self.default_adhoc_schedule_name = 'adhoc-schedule'
        self.default_adhoc_project_name = 'default-project'
        self.default_adhoc_schedule_key = self.default_adhoc_project_name + '::' + self.default_adhoc_schedule_name
        self.default_environment_config = '/sso/sfw/ghusps-toolkit/config/environment/environment_config.json'
        self.default_sas_root = '/sso/biconfig/940/Lev1'
        self.default_sas_logs = os.path.join(self.default_sas_root, 'Logs')
        self.default_smc_path = os.path.join(self.default_sas_root, 'SchedulingServer', 'RunNow')
        self.default_migs_log = '/sso/biconfig/930/Lev1/Applications/SASMerchIntelGridSvr5.2/Logs/MerchIntelGridSvr.log'
        self.my_hostname = str(socket.getaddrinfo(socket.gethostname(), 0, 0, 0, 0, socket.AI_CANONNAME)[0][3]).strip()
        match = re.match('(\D+)\d', self.my_hostname)
        if match:
            self.default_tla = match.group(1).upper()
        else:
            self.default_tla = None
        self.logging_level = logging.CRITICAL  # type: int
        self.default_zabbix_key_no_schedule = 'toolkit.jibbix_options'
        # Start JibbixOptions Defaults
        # Dynamically import the Config module
        # The dependency on JibbixOptions in the Config package causes import issues
        from pydoc import locate
        self.AMSJibbixOptions = locate('Toolkit.Config.AMSJibbixOptions')()
        self.AMSJibbixOptions.assignee = 'ssoretailops'
        self.AMSJibbixOptions.priority = 'CRITICAL'
        self.AMSJibbixOptions.project = 'SSO'
        self.AMSJibbixOptions.labels = 'ams_toolkit, ams_adhoc_schedule'
        self.AMSJibbixOptions.raw_config = {
            'assignee': 'ssoretailops',
            'priority': 'CRITICAL',
            'project': 'SSO',
            'labels': 'ams_toolkit, ams_adhoc_schedule'
        }
        self.jira_base = 'https://www.ondemand.sas.com/jira/'
        self.test_jira_retries = 3
        self.test_jira_description = 'This is a test ticket to ensure that AMS Batch Monitoring is correctly configured.  Please ignore and a team member will close this accordingly.'
        self.test_jira_summary = 'Testing AMS Batch Monitoring for Host: {}'
        # End JibbixOptions Defaults

        # Start File Routing Defaults
        self.file_route_default_retry_wait = 30
        self.file_route_default_retry_limit = 5
        self.file_route_default_polling_interval = 300
        self.file_route_default_max_iterations = 30
        # End File Routing Defaults

        # Start FileHandler Defaults
        self.file_handler_allowed_types = [
            'Compress',
            'Delete',
            'Archive'
        ]
        self.file_handler_allowed_levels = [
            'File',
            'Directory'
        ]
        self.file_handler_default_file_pattern = '*.*'
        self.file_handler_default_follow_symlinks = "No"
        self.file_handler_allowed_follow_symlinks = [
            'Yes',
            'No'
        ]
        self.file_handler_default_archive_directory = '../archive'
        # End FileHandler Defaults

        # Start FileParser Defaults
        self.file_parser_default_file_pattern = '*.*'
        self.file_parser_default_search_pattern = '^PATTERN$'
        self.file_parser_default_follow_symlinks = False
        self.file_parser_action_types = [
            'Zabbix',
            'Email',
            'TouchFile',
            'ClearSignal',
            'Script',
            'None'
        ]
        # End FileParser Defaults

        # Start Dependency Checker Defaults
        self.dependency_checker_default_max_attempts = 60
        self.dependency_checker_default_attempt_interval = 60  # seconds
        self.dependency_checker_allowed_types = [
            'IncomingFileMulti',
            'IncomingFileSingle',
            'PortDown',
            'PortUp',
            'Script',
            'SignalFilePresent',
            'SignalFileAbsent',
            'ScheduleNotRunning',
            'DQ'
        ]
        # End Dependency Checker Defaults

        # Start Complete Handler Defaults
        self.complete_handler_allowed_types = [
            "TouchFile",
            "ClearSignal",
            "Script",
            "MIGridServerErrors",
            "STPHealthCheck",
            "SmokeTest"
        ]
        # End Complete Handler Defaults

        # Start Logger Defaults
        self.logger_default_max_mbytes = 5
        self.logger_default_backup_count = 20
        # End Logger Defaults

        # Start scheduling defaults #
        self.default_sso_run_path = '/sso/common/bin/sso_run.pl'
        self.perl_5_lib = '/sso/common/bin'
        self.default_automation_type = 'SSORun'
        self.default_adi_run_path = 'data_intake.pl'
        self.default_sked_path = os.path.join(AMSDefaults.get_app_path(), 'Sked', 'sked')
        self.default_sked_plugin = os.path.join(AMSDefaults.get_app_path(), 'Sked', 'sked_plugin.py')
        self.available_automation_programs = [
            'SSORun',
            'Sked',
            'ADI',
            'SMC',
            'Script',
            'Job_Flow'
        ]
        self.automation_programs_with_config_file = [
            'SSORun',
            'Sked',
            'ADI'
        ]
        self.available_dependency_check_policies = [
            'Error After First Fail (serial)',
            'Run All (serial)'
        ]
        # End scheduling defaults #

        # Start STP Defaults #
        self.thycotic_func_username = 'AY4b0Pjxc799tJBun1KyOLXkxFYcgboRy9KKGW0RcM0='
        self.thycotic_func_password = 'gt4vgcmScL2BBj7xDAXo9w=='
        self.default_mi_secret_id = 71466
        self.default_zabbix_secret_id = 109733
        self.default_web_proxy = 'http://webproxy.vsp.sas.com:3128'
        self.default_timeout = 30
        self.default_stp_error_to_email_address = 'ssoretailops@wnt.sas.com'
        self.default_stp_max_workers = 50
        self.default_stp_thread_timer_check_interval = 5
        self.default_stp_secret_id = 71466
        self.default_confluence_space = 'SSODMAS'  # type: str
        self.default_confluence_secret_id = 104944
        self.confluence_root = 'https://www.ondemand.sas.com/confluencedoc'
        self.default_issues_jira_link = self.confluence_root + '/x/-R5VAg'
        self.default_stp_jira_link = self.default_issues_jira_link + '#HandlingIssues-STPHealthCheck'
        self.default_smoketest_jira_link = self.default_issues_jira_link + '#HandlingIssues-SmokeTest'
        # End STP Defaults #

        # Start SmokeTest Defaults #
        self.smoke_test_default_retry_limit = 2
        self.smoke_test_default_retry_timeout = 300
        # End SmokeTest Defaults #

        # ams_schedules_low_level_discovery current_user #
        try:
            self.current_user = None
            self.current_user = subprocess.check_output('logname', stderr=subprocess.STDOUT).strip()
        except subprocess.CalledProcessError as e:
            pass
        if self.current_user is None or len(self.current_user) == 0:
            self.current_user = getpass.getuser()

        # start RMSS #
        self.rmss_default_dummy_host = 'rmss_dummy_host'
        self.rmss_default_supplemental_jibbix_options = "/sso/sfw/ghusps-toolkit/config/rmss/{}.json"
        # end RMSS #

    @staticmethod
    def is_dev_host(hostname=None):
        if hostname is None:
            hostname = str(socket.getaddrinfo(socket.gethostname(), 0, 0, 0, 0, socket.AI_CANONNAME)[0][3]).strip()
        if hostname in ['ams-toolkit', 'rmss_dummy_host']:
            return True
        return False

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass