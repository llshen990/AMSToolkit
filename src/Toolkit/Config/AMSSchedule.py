import collections
import sys
from pydoc import locate
from os.path import expanduser

import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSAttributeMapper, AbstractAMSConfig, AMSCommentable, AMSConfigModelAttribute, AMSJibbixOptions
from Toolkit.Exceptions import AMSScheduleException, AMSValidationException
from lib.Helpers.OutputFormatHelper import OutputFormatHelper

class AMSSchedule(AMSCommentable):
    """
       This class defines the markets / environments
       """

    def __init__(self):
        self.AMSDefaults = locate('Toolkit.Lib.Defaults.AMSDefaults')()
        AMSCommentable.__init__(self)
        self.raw_config = collections.OrderedDict()
        self.project_name = None  # this will be defined when load is invoked
        self.schedule_name = None  # this needs to match the class name if it's the ams toolkit automation
        self.flow_identifier = None
        self.started_ola = None  # type: str
        self.completed_ola = None  # type: str
        self.tla = None  # type: str
        self.start_stop_comment_link  = None # type: str
        self.schedule_update_comment_link = None  # type: str
        self.home_dir = None  # type: str
        self.signal_dir = None  # type: str
        self.automation_type = None  # type: str
        self.dependency_check_policy = None  # type: str
        self.schedule_config_file = None  # type: str
        self.smc_root_dir = None # type: str
        self.flow_auth_file = None # type: str
        self.flow_id = None # type: str
        self.automation_name = None  # type: str
        self.longtime = None  # type: int
        self.longtime_priority = None  # type: str
        self.shorttime = None  # type: int
        self.incoming_dir = None  # type: str
        self.archive_dir = None  # type: str
        self.outgoing_dir = None  # type: str
        self.AMSJibbixOptions = AMSJibbixOptions()
        self.dependency_jibbix_options = collections.OrderedDict()
        self.AMSDependencyJibbixOptions = AMSJibbixOptions()
        self.longtime_jibbix_options = collections.OrderedDict()
        self.AMSLongtimeJibbixOptions = AMSJibbixOptions()
        self.num_ams_dependency_checkers = None  # type: int
        self.num_ams_log_files = None  # type: int
        self.num_on_error_handlers = None  # type: int
        self.num_on_success_handlers = None  # type: int
        self.AMSDependencyChecks = collections.OrderedDict()  # type: dict[str, AMSDependencyChecker]
        self.AMSLogFiles = collections.OrderedDict()  # type: dict[str, AMSLogFile]
        self.AMSSuccessCompleteHandler = collections.OrderedDict()  # type: dict[str, AMSSuccessCompleteHandler]
        self.AMSErrorCompleteHandler = collections.OrderedDict()  # type: dict[str, AMSErrorCompleteHandler]

        self.sso_run_path = self.AMSDefaults.default_sso_run_path
        self.sso_run_perl_5_lib = self.AMSDefaults.perl_5_lib
        self.sked_path = self.AMSDefaults.default_sked_path

    def get_config_dict_key(self):
        return self.schedule_name

    def get_static_config_dict_key(self):
        return 'schedules'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Debug
        debug_attrs = AMSConfigModelAttribute()
        debug_attrs.set_required(False)
        debug_attrs.set_default(False)
        debug_attrs.set_label('Debug')
        debug_attrs.set_type('bool')
        debug_attrs.set_options([
            True,
            False
        ])
        debug_attrs.set_mapped_class_variable('debug')
        self.config_model_attributes['debug'] = debug_attrs

        # Automation Type
        automation_type_attrs = AMSConfigModelAttribute()
        automation_type_attrs.set_required(True)
        automation_type_attrs.set_default(self.AMSDefaults.default_automation_type)
        automation_type_attrs.set_label('Automation Type')
        automation_type_attrs.set_type('str')
        automation_type_attrs.set_options(self.AMSDefaults.available_automation_programs)
        automation_type_attrs.set_mapped_class_variable('automation_type')
        self.config_model_attributes['automation_type'] = automation_type_attrs

        # Automation Name, or Script Name
        schedule_name_attrs = AMSConfigModelAttribute()
        schedule_name_attrs.set_required(True)
        schedule_name_attrs.set_default(None)
        schedule_name_attrs.set_label('Automation name or full path to automation script')
        schedule_name_attrs.set_type('str')
        schedule_name_attrs.set_is_config_dict_key(True)
        schedule_name_attrs.set_mapped_class_variable('schedule_name')
        self.config_model_attributes['schedule_name'] = schedule_name_attrs

        # Flow Identifier
        flow_identifier_attrs = AMSConfigModelAttribute()
        flow_identifier_attrs.set_required(False)
        flow_identifier_attrs.set_label('Identifier for the SMC flow (or blank for most recent)')
        flow_identifier_attrs.set_type('str')
        flow_identifier_attrs.set_dependent_variable('automation_type')
        flow_identifier_attrs.set_dependent_value('SMC')
        flow_identifier_attrs.set_mapped_class_variable('flow_identifier')
        self.config_model_attributes['flow_identifier'] = flow_identifier_attrs

        # SMC Root Dir
        smc_root_dir_attrs = AMSConfigModelAttribute()
        smc_root_dir_attrs.set_required(False)
        smc_root_dir_attrs.set_default(self.AMSDefaults.default_smc_path)
        smc_root_dir_attrs.set_label('SMC root directory for this flow')
        smc_root_dir_attrs.set_type('str')
        smc_root_dir_attrs.set_dependent_variable('automation_type')
        smc_root_dir_attrs.set_dependent_value('SMC')
        smc_root_dir_attrs.set_mapped_class_variable('smc_root_dir')
        self.config_model_attributes['smc_root_dir'] = smc_root_dir_attrs

        # Job Flow auth file
        flow_auth_file_attrs = AMSConfigModelAttribute()
        flow_auth_file_attrs.set_required(True)
        flow_auth_file_attrs.set_default('{}/.auth'.format(expanduser('~')))
        flow_auth_file_attrs.set_label('Path to auth file containing authentication token')
        flow_auth_file_attrs.set_type('str')
        flow_auth_file_attrs.set_dependent_variable('automation_type')
        flow_auth_file_attrs.set_dependent_value('Job_Flow')
        flow_auth_file_attrs.set_mapped_class_variable('flow_auth_file')
        self.config_model_attributes['flow_auth_file'] = flow_auth_file_attrs

        # Job Flow uuid
        flow_id_attrs = AMSConfigModelAttribute()
        flow_id_attrs.set_required(True)
        flow_id_attrs.set_label('UUID of job flow as found in Environment Manager')
        flow_id_attrs.set_type('str')
        flow_id_attrs.set_dependent_variable('automation_type')
        flow_id_attrs.set_dependent_value('Job_Flow')
        flow_id_attrs.set_mapped_class_variable('flow_id')
        self.config_model_attributes['flow_id'] = flow_id_attrs

        # Schedule Home Directory
        home_dir_attrs = AMSConfigModelAttribute()
        home_dir_attrs.set_required(True)
        home_dir_attrs.set_default(None)
        home_dir_attrs.set_label('Schedule Home Directory')
        home_dir_attrs.set_type('str')
        home_dir_attrs.set_mapped_class_variable('home_dir')
        home_dir_attrs.set_return_transform('abspath')
        self.config_model_attributes['home_dir'] = home_dir_attrs

        # Signal Directory
        signal_dir_attrs = AMSConfigModelAttribute()
        signal_dir_attrs.set_required(True)
        signal_dir_attrs.set_default(None)
        signal_dir_attrs.set_label('Signal Directory')
        signal_dir_attrs.set_type('str')
        signal_dir_attrs.set_mapped_class_variable('signal_dir')
        signal_dir_attrs.set_return_transform('abspath')
        self.config_model_attributes['signal_dir'] = signal_dir_attrs

        # Automation Config File (config.txt)
        schedule_config_file_attrs = AMSConfigModelAttribute()
        schedule_config_file_attrs.set_required(True)
        if AMSAttributeMapper().is_set_attribute('home_dir') and AMSAttributeMapper().get_attribute('home_dir'):
            schedule_config_file_attrs.set_default(AMSAttributeMapper().get_attribute('home_dir') + '/conf')
        else:
            schedule_config_file_attrs.set_default(None)
        schedule_config_file_attrs.set_label("Path to automation schedule 'config.txt' or 'sked.ini'")
        schedule_config_file_attrs.set_type('str')
        schedule_config_file_attrs.set_mapped_class_variable('schedule_config_file')
        schedule_config_file_attrs.set_dependent_variable('automation_type')
        for auto_type in self.AMSDefaults.automation_programs_with_config_file:
            schedule_config_file_attrs.set_dependent_value(auto_type)
        self.config_model_attributes['schedule_config_file'] = schedule_config_file_attrs

        # TLA
        tla_attrs = AMSConfigModelAttribute()
        tla_attrs.set_required(True)
        if self.AMSDefaults.default_tla:
            tla_attrs.set_default(self.AMSDefaults.default_tla)
        else:
            tla_attrs.set_default(None)
        tla_attrs.set_label('TLA')
        tla_attrs.set_type('str')
        tla_attrs.set_mapped_class_variable('tla')
        self.config_model_attributes['tla'] = tla_attrs

        # Add a Comment in the linked JIRA ticket for the schedule for start / stop notification
        start_stop_comment_link_attrs = AMSConfigModelAttribute()
        start_stop_comment_link_attrs.set_required(False)
        start_stop_comment_link_attrs.set_default('comm')
        start_stop_comment_link_attrs.set_label('Schedule Start / Stop comment Link (empty for no comment, comm, or a specific JIRA ticket)')
        start_stop_comment_link_attrs.set_type('str')
        start_stop_comment_link_attrs.set_mapped_class_variable('start_stop_comment_link')
        self.config_model_attributes['start_stop_comment_link'] = start_stop_comment_link_attrs

        # Add a Comment in the linked JIRA ticket for the schedule with the results
        schedule_update_comment_link_attrs = AMSConfigModelAttribute()
        schedule_update_comment_link_attrs.set_required(False)
        start_stop_comment_link_attrs.set_default(None)
        schedule_update_comment_link_attrs.set_label('Schedule Stats Update Comment Link (empty for no comment, comm, or a specific JIRA ticket)')
        schedule_update_comment_link_attrs.set_type('str')
        schedule_update_comment_link_attrs.set_mapped_class_variable('schedule_update_comment_link')
        self.config_model_attributes['schedule_update_comment_link'] = schedule_update_comment_link_attrs

        # Longtime
        longtime_attrs = AMSConfigModelAttribute()
        longtime_attrs.set_required(False)
        longtime_attrs.set_default(None)
        longtime_attrs.set_label('Longtime (Trigger if schedule runs longer than x seconds)')
        longtime_attrs.set_type('int')
        longtime_attrs.set_mapped_class_variable('longtime')
        self.config_model_attributes['longtime'] = longtime_attrs

        # Shorttime
        shorttime_attrs = AMSConfigModelAttribute()
        shorttime_attrs.set_required(False)
        shorttime_attrs.set_default(None)
        shorttime_attrs.set_label('Shorttime (Trigger if schedule runs shorter than x seconds)')
        shorttime_attrs.set_type('int')
        shorttime_attrs.set_mapped_class_variable('shorttime')
        self.config_model_attributes['shortime'] = shorttime_attrs

        # Longtime Priority
        longtime_priority_attrs = AMSConfigModelAttribute()
        longtime_priority_attrs.set_required(False)
        longtime_priority_attrs.set_default(None)
        longtime_priority_attrs.set_label('Longtime Priority (if not blank, overrides schedule\'s Jibbix priority)')
        longtime_priority_attrs.set_type('str')
        longtime_priority_attrs.set_mapped_class_variable('longtime_priority')
        self.config_model_attributes['longtime_priority'] = longtime_priority_attrs

        AMSCommentable._set_config_model_attributes(self)

        # Incoming Dir
        incoming_dir_attrs = AMSConfigModelAttribute()
        incoming_dir_attrs.set_required(False)
        incoming_dir_attrs.set_default(None)
        incoming_dir_attrs.set_label('Incoming Directory override for this schedule')
        incoming_dir_attrs.set_type('str')
        incoming_dir_attrs.set_mapped_class_variable('incoming_dir')
        incoming_dir_attrs.set_return_transform('abspath')
        self.config_model_attributes['incoming_dir'] = incoming_dir_attrs

        # Archive Dir
        archive_dir_attrs = AMSConfigModelAttribute()
        archive_dir_attrs.set_required(False)
        archive_dir_attrs.set_default(None)
        archive_dir_attrs.set_label('Archive Directory override for this schedule')
        archive_dir_attrs.set_type('str')
        archive_dir_attrs.set_mapped_class_variable('archive_dir')
        archive_dir_attrs.set_return_transform('abspath')
        self.config_model_attributes['archive_dir'] = archive_dir_attrs

        # Outgoing Dir
        outgoing_dir_attrs = AMSConfigModelAttribute()
        outgoing_dir_attrs.set_required(False)
        outgoing_dir_attrs.set_default(None)
        outgoing_dir_attrs.set_label('Outgoing Directory override for this schedule')
        outgoing_dir_attrs.set_type('str')
        outgoing_dir_attrs.set_mapped_class_variable('outgoing_dir')
        outgoing_dir_attrs.set_return_transform('abspath')
        self.config_model_attributes['outgoing_dir'] = outgoing_dir_attrs

        # Dependency Check Policy
        dependency_check_policy_attrs = AMSConfigModelAttribute()
        dependency_check_policy_attrs.set_required(True)
        dependency_check_policy_attrs.set_default(self.AMSDefaults.available_dependency_check_policies[0])
        dependency_check_policy_attrs.set_label('Dependency Check Policy')
        dependency_check_policy_attrs.set_type('str')
        dependency_check_policy_attrs.set_options(self.AMSDefaults.available_dependency_check_policies)
        dependency_check_policy_attrs.set_mapped_class_variable('dependency_check_policy')
        self.config_model_attributes['dependency_check_policy_attrs'] = dependency_check_policy_attrs

        # AMSJibbixOptions
        ams_jibbix_options_attrs = AMSConfigModelAttribute()
        ams_jibbix_options_attrs.set_required(False)
        ams_jibbix_options_attrs.set_default(1)
        ams_jibbix_options_attrs.set_max_allowed_entries(1)
        ams_jibbix_options_attrs.set_options([
            1,
            0
        ])
        ams_jibbix_options_attrs.set_label('Set Jibbix Options For This Schedule?')
        ams_jibbix_options_attrs.set_type('int')
        ams_jibbix_options_attrs.set_linked_type('Toolkit.Config.AMSJibbixOptions')
        ams_jibbix_options_attrs.set_linked_object('Toolkit.Config.AMSJibbixOptions')
        ams_jibbix_options_attrs.set_linked_label('Setup Jibbix Options')
        ams_jibbix_options_attrs.set_mapped_class_variable('AMSJibbixOptions')
        ams_jibbix_options_attrs.set_return_map_to_variable('AMSJibbixOptions')
        self.config_model_attributes['AMSJibbixOptions'] = ams_jibbix_options_attrs

        # AMSDependencyJibbixOptions
        ams_dependency_jibbix_options_attrs = AMSConfigModelAttribute()
        ams_dependency_jibbix_options_attrs.set_required(False)
        ams_dependency_jibbix_options_attrs.set_label('Set Jibbix Options For Dependency Checks?')
        ams_dependency_jibbix_options_attrs.set_type('dict')
        ams_dependency_jibbix_options_attrs.set_allow_edit(False)
        ams_dependency_jibbix_options_attrs.set_hide_from_user_display(True)
        ams_dependency_jibbix_options_attrs.set_mapped_class_variable('dependency_jibbix_options')
        self.config_model_attributes['dependency_jibbix_options'] = ams_dependency_jibbix_options_attrs

        # Num AMS Dependency Checkers
        num_ams_dependency_checkers_attrs = AMSConfigModelAttribute()
        num_ams_dependency_checkers_attrs.set_required(False)
        num_ams_dependency_checkers_attrs.set_default(0)
        num_ams_dependency_checkers_attrs.set_label('How many dependency checks would you like to setup?')
        num_ams_dependency_checkers_attrs.set_type('int')
        num_ams_dependency_checkers_attrs.set_num_required_entries(0)
        num_ams_dependency_checkers_attrs.set_linked_object('Toolkit.Config.AMSDependencyChecker')
        num_ams_dependency_checkers_attrs.set_linked_type('dict')
        num_ams_dependency_checkers_attrs.set_linked_label('Dependency Check Setup')
        num_ams_dependency_checkers_attrs.set_return_map_to_variable('AMSDependencyChecks')
        num_ams_dependency_checkers_attrs.set_mapped_class_variable('num_ams_dependency_checkers')
        self.config_model_attributes['num_ams_dependency_checkers'] = num_ams_dependency_checkers_attrs

        # On Error Handlers
        num_on_error_handlers_attrs = AMSConfigModelAttribute()
        num_on_error_handlers_attrs.set_required(False)
        num_on_error_handlers_attrs.set_default(0)
        num_on_error_handlers_attrs.set_label('Number of on error handler(s)')
        num_on_error_handlers_attrs.set_type('int')
        num_on_error_handlers_attrs.set_num_required_entries(0)
        num_on_error_handlers_attrs.set_linked_object('Toolkit.Config.AMSErrorCompleteHandler')
        num_on_error_handlers_attrs.set_linked_type('dict')
        num_on_error_handlers_attrs.set_linked_label('On Error Handlers Setup')
        num_on_error_handlers_attrs.set_include_in_config_file(True)
        num_on_error_handlers_attrs.set_return_map_to_variable('AMSErrorCompleteHandler')
        num_on_error_handlers_attrs.set_mapped_class_variable('num_on_error_handlers')
        self.config_model_attributes['num_on_error_handlers'] = num_on_error_handlers_attrs

        # On Success Handlers
        num_on_success_handlers_attrs = AMSConfigModelAttribute()
        num_on_success_handlers_attrs.set_required(False)
        num_on_success_handlers_attrs.set_default(0)
        num_on_success_handlers_attrs.set_label('Number of on success handler(s)')
        num_on_success_handlers_attrs.set_type('int')
        num_on_success_handlers_attrs.set_num_required_entries(0)
        num_on_success_handlers_attrs.set_linked_object('Toolkit.Config.AMSSuccessCompleteHandler')
        num_on_success_handlers_attrs.set_linked_type('dict')
        num_on_success_handlers_attrs.set_linked_label('On Success Handlers Setup')
        num_on_success_handlers_attrs.set_include_in_config_file(True)
        num_on_success_handlers_attrs.set_return_map_to_variable('AMSSuccessCompleteHandler')
        num_on_success_handlers_attrs.set_mapped_class_variable('num_on_success_handlers')
        self.config_model_attributes['num_on_success_handlers'] = num_on_success_handlers_attrs

    def load(self, project_name, schedule_name, config_dict):
        """
        :param project_name: project name from the config dict.
        :type project_name: str
        :param schedule_name: schedule name from the config dict.
        :type schedule_name: str
        :param config_dict: AMS config dictionary (JSON)
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.project_name = project_name
            self.schedule_name = schedule_name
            self._read_string('flow_identifier')
            self._read_string('smc_root_dir')
            if not self.smc_root_dir:
                self.smc_root_dir = self.AMSDefaults.default_smc_path
            self._read_string('flow_auth_file')
            self._read_string('flow_id')
            self._read_debug()
            self._read_tla()
            self._read_string('start_stop_comment_link')
            self._read_string('schedule_update_comment_link')
            self._read_string('dependency_check_policy')
            if not self.dependency_check_policy:
                self.dependency_check_policy = self.AMSDefaults.available_dependency_check_policies[0]
            self._read_home_dir()
            self._read_signal_dir()
            self._read_automation_type()
            self._read_schedule_config_file()
            self._read_automation_name()
            self._read_longtime()
            self._read_longtime_priority()
            self._read_shorttime()
            AMSCommentable.load(self)
            self._read_incoming_dir()
            self._read_outgoing_dir()
            self._read_archive_dir()
            self._read_dependency_checks()
            self._read_jibbix_options(self.schedule_name, self.AMSJibbixOptions)
            if self._read_json('dependency_jibbix_options'):
                self._read_jibbix_options(self.schedule_name, self.AMSDependencyJibbixOptions, key='AMSDependencyJibbixOptions', json_key='dependency_jibbix_options')
            else:
                # ensure jibbix_options dict and object are None if it can't be read
                self.dependency_jibbix_options = None
                self.AMSDependencyJibbixOptions = None
            if self._read_json('longtime_jibbix_options'):
                self._read_jibbix_options(self.schedule_name, self.AMSLongtimeJibbixOptions, key='AMSLongtimeJibbixOptions', json_key='longtime_jibbix_options')
            else:
                # ensure longtime_jibbix_options dict and object are None if it can't be read
                self.longtime_jibbix_options = None
                self.AMSLongtimeJibbixOptions = None
            self._read_log_file_locations()
            self._read_on_error_handlers()
            self._read_on_success_handlers()
        except AMSScheduleException:
            raise
        except Exception as e:
            raise AMSScheduleException(e)

    def _read_tla(self):
        """
        This method will set the tla variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'tla' in self.raw_config and self.raw_config['tla']:
            self.tla = str(self.raw_config['tla']).strip()
        else:
            self.AMSLogger.debug('tla is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_home_dir(self):
        """
        This method will set the home_dir variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'home_dir' in self.raw_config and self.raw_config['home_dir']:
            self.home_dir = str(self.raw_config['home_dir']).strip()
        else:
            self.AMSLogger.debug('home_dir is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_signal_dir(self):
        """
        This method will set the signal_dir variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'signal_dir' in self.raw_config and self.raw_config['signal_dir']:
            self.signal_dir = str(self.raw_config['signal_dir']).strip()
        else:
            self.AMSLogger.debug('signal_dir is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_automation_type(self):
        """
        This method will set the automation_type variable for the schedule.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'automation_type' in self.raw_config and self.raw_config['automation_type']:
            self.automation_type = str(self.raw_config['automation_type']).strip()
            if self.automation_type not in self.get_config_attributes('automation_type').options:
                self.AMSLogger.debug('automation_type of ' + str(self.automation_type) + ' is not supported.  The following automation types are supported: ' + OutputFormatHelper.join_output_from_list(self.get_config_attributes('automation_type').options))
                return False
        else:
            self.AMSLogger.debug('automation_type is not defined for the following schedule and it is required: ' + self.schedule_name + '.')
            return False

        return True

    def _read_schedule_config_file(self):
        """
        This method will set the schedule_config_file variable for the schedule.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'schedule_config_file' in self.raw_config and self.raw_config['schedule_config_file']:
            self.schedule_config_file = str(self.raw_config['schedule_config_file']).strip()
        else:
            self.AMSLogger.debug('schedule_config_file is not defined for the following schedule and it is required: ' + self.schedule_name + '.')
            return False

        return True

    def _read_automation_name(self):
        """
        This method will set the automation_name variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'automation_name' in self.raw_config and self.raw_config['automation_name']:
            self.automation_name = str(self.raw_config['automation_name']).strip()
        else:
            self.AMSLogger.debug('automation_name is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_longtime(self):
        """
        This method will set the longtime variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'longtime' in self.raw_config and self.raw_config['longtime']:
            self.longtime = int(str(self.raw_config['longtime']).strip())
        else:
            self.AMSLogger.debug('longtime is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_longtime_priority(self):
        """
        This method will set the longtime_priority variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'longtime_priority' in self.raw_config and self.raw_config['longtime_priority']:
            self.longtime_priority = str(self.raw_config['longtime_priority']).strip()
        else:
            self.AMSLogger.debug(
                'longtime_priority is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_shorttime(self):
        """
        This method will set the shorttime variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'shorttime' in self.raw_config and self.raw_config['shorttime']:
            self.shorttime = int(str(self.raw_config['shorttime']).strip())
        else:
            self.AMSLogger.debug('shorttime is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_incoming_dir(self):
        """
        This method will set the incoming_dir variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'incoming_dir' in self.raw_config and self.raw_config['incoming_dir']:
            self.incoming_dir = str(self.raw_config['incoming_dir']).strip()
        else:
            self.AMSLogger.debug('incoming_dir is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_outgoing_dir(self):
        """
        This method will set the outgoing_dir variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'outgoing_dir' in self.raw_config and self.raw_config['outgoing_dir']:
            self.outgoing_dir = str(self.raw_config['outgoing_dir']).strip()
        else:
            self.AMSLogger.debug('outgoing_dir is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_archive_dir(self):
        """
        This method will set the archive_dir variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'archive_dir' in self.raw_config and self.raw_config['archive_dir']:
            self.archive_dir = str(self.raw_config['archive_dir']).strip()
        else:
            self.AMSLogger.debug('archive_dir is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_dependency_checks(self):
        """
        This method will set the AMSDependencyChecks attribute for the schedule by loading AMSDependencyChecker objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'dependency_checks' in self.raw_config and self.raw_config['dependency_checks']:
            self.num_ams_dependency_checkers = 0
            for dependency_check_name, dependency_check in self.raw_config['dependency_checks'].iteritems():
                self.num_ams_dependency_checkers += 1
                ams_dependency_checker = locate('Toolkit.Config.AMSDependencyChecker')()
                ams_dependency_checker.load(dependency_check_name, dependency_check, self.schedule_name)
                self.AMSDependencyChecks[dependency_check_name] = ams_dependency_checker
        else:
            self.AMSLogger.debug('log_file_locations is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_log_file_locations(self):
        """
        This method will set the AMSLogFiles attribute for the schedule by loading AMSLogFile objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'log_file_locations' in self.raw_config and self.raw_config['log_file_locations']:
            self.num_ams_log_files = 0
            for logfile_path, error_pattern_list in self.raw_config['log_file_locations'].iteritems():
                self.num_ams_log_files += 1
                ams_log_file = locate('Toolkit.Config.AMSLogFile')()
                ams_log_file.load(logfile_path, error_pattern_list)
                self.AMSLogFiles[logfile_path] = ams_log_file
        else:
            self.AMSLogger.debug('log_file_locations is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_on_error_handlers(self):
        """
        This method will set the on_error_handlers variable for the schedule.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'error_complete_handler' in self.raw_config and self.raw_config['error_complete_handler']:
            self.num_on_error_handlers = 0
            for complete_handler_name, complete_handler in self.raw_config['error_complete_handler'].iteritems():
                self.num_on_error_handlers += 1
                ams_complete_handler = locate('Toolkit.Config.AMSErrorCompleteHandler')()
                ams_complete_handler.load(complete_handler_name, complete_handler, self.schedule_name)
                self.AMSErrorCompleteHandler[complete_handler_name] = ams_complete_handler
        else:
            self.AMSLogger.debug('On Error Handler(s) are not defined in the config for the following schedule: ' + self.schedule_name + '.')
            return False

        return True

    def _read_on_success_handlers(self):
        """
        This method will set the on_success_handlers variable for the schedule.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'success_complete_handler' in self.raw_config and self.raw_config['success_complete_handler']:
            self.num_on_success_handlers = 0
            for complete_handler_name, complete_handler in self.raw_config['success_complete_handler'].iteritems():
                self.num_on_success_handlers += 1
                ams_complete_handler = locate('Toolkit.Config.AMSSuccessCompleteHandler')()
                ams_complete_handler.load(complete_handler_name, complete_handler, self.schedule_name)
                self.AMSSuccessCompleteHandler[complete_handler_name] = ams_complete_handler
        else:
            self.AMSLogger.debug('On Success Handler(s) are not defined in the config for the following schedule: ' + self.schedule_name + '.')
            return False

        return True

    def get_schedule_zabbix_key(self):
        return self.project_name + '::' + self.schedule_name

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass

    def _validate_schedule_name(self, tmp_input):
        if self.automation_type in ('SSORun', 'Sked', 'Script'):
            # Ensure path is absolute and not relative
            if not str(tmp_input).startswith(os.path.sep):
                raise AMSValidationException('Schedule name for SSORun, Sked, and Bash script must be an absolute path')
            # Also ensure the path exists
            return self._ams_validate_file(tmp_input)
        else:
            # Nothing to validate for automation name if SMC or ADI
            return True

    def _validate_schedule_config_file(self, tmp_input):
        return self._ams_validate_file(tmp_input)

    def _validate_home_dir(self, tmp_input):
        return self._ams_validate_directory(tmp_input)

    def _validate_signal_dir(self, tmp_input):
        return self._ams_validate_directory(tmp_input)

    def _validate_incoming_dir(self, tmp_input):
        if len(tmp_input) == 0:
            return True
        return self._ams_validate_directory(tmp_input)

    def _validate_archive_dir(self, tmp_input):
        if len(tmp_input) == 0:
            return True
        return self._ams_validate_directory(tmp_input)

    def _validate_outgoing_dir(self, tmp_input):
        if len(tmp_input) == 0:
            return True
        return self._ams_validate_directory(tmp_input)
