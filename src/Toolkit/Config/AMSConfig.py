import os, json, socket, collections, datetime, shutil, sys
from pydoc import locate

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSEnvironment, AMSProject, AMSOla, AbstractAMSConfig, AMSConfigModelAttribute, AMSFileRoute, AMSSchedule, AMSSecret, AMSMIHealthCheck, AMSWebScenario, AMSFileHandler, AMSFileParser
from lib.Validators import FileExistsValidator, UrlValidator, EmailValidator
from Toolkit.Exceptions import AMSConfigException, AMSEnvironmentException, AMSJibbixOptionsException, AMSLogFileException, AMSOlaException, AMSProjectException, AMSScheduleException, AMSConfigSyntaxException

DEFAULT_CONFIG_PATH = os.path.join(APP_PATH, 'Toolkit', 'Config', 'ams_config.json')
DEFAULT_MAX_WORKERS = 3  # type: int
DEFAULT_TIMER_CHECK_INTERVAL = 30  # type: int


class AMSConfig(AbstractAMSConfig):
    def __init__(self, config_path=None, allow_config_generation=False, always_new=False, test_config_path_permissions=False):
        self.AMSDefaults = locate('Toolkit.Lib.Defaults.AMSDefaults')()
        AbstractAMSConfig.__init__(self)

        self.always_new_config = always_new
        self.new_config = False
        # configs versions
        self.config_version = self.AMSDefaults.config_version

        if not config_path:
            self.config_path = DEFAULT_CONFIG_PATH
        else:
            self.config_path = config_path

        self.config_path = os.path.abspath(self.config_path)

        self.config_dir = os.path.dirname(self.config_path)
        self.backup_config_dir = os.path.join(self.config_dir, 'config_backups')
        self.valid_config = True

        self.fev = FileExistsValidator(self.debug)

        if not self.fev.validate(self.config_path):
            self.AMSLogger.debug("No config file exists at location " + str(self.config_path))
            if not allow_config_generation:
                self.valid_config = False
            self.new_config = True

        if self.new_config and allow_config_generation and test_config_path_permissions:
            if not self.fev.directory_writeable(os.path.dirname(self.config_path)):
                raise AMSConfigSyntaxException('Directory is not writeable: %s' % os.path.dirname(self.config_path))

        self.incoming_dir = None  # type: str
        self.archive_dir = None  # type: str
        self.outgoing_dir = None  # type: str
        self.multi_thread_max_workers = None  # type: int
        self.multi_thread_timer_check_interval = None  # type: int
        self.run_user = None  # type: str
        self.runbook_link = None  # type: str

        self.num_ams_environments = None  # type: int
        self.AMSEnvironments = collections.OrderedDict()  # type: dict[str, AMSEnvironment]

        self.num_ams_projects = None  # type: int
        self.AMSProjects = collections.OrderedDict()  # type: dict[AMSProject]

        self.num_ams_olas = None  # type: int
        self.AMSOlas = collections.OrderedDict()  # type: dict[AMSOla]

        self.raw_config = collections.OrderedDict()
        self.new_raw_config = collections.OrderedDict()

        self.num_ams_file_routes = None  # type: int
        self.AMSFileRoutes = collections.OrderedDict()  # type: dict[str, AMSFileRoute]

        self.error_email_to_address = None  # type: str

        self.ams_event_handler = None

        self.num_ams_secrets = None  # type: int
        self.AMSSecrets = collections.OrderedDict()  # type: dict[str, AMSSecret]

        self.num_ams_mihealthchecks = None  # type: int
        self.AMSMIHealthChecks = collections.OrderedDict()  # type: dict[str, AMSMIHealthCheck]

        self.num_ams_web_scenarios = None  # type: int
        self.AMSWebScenarios = collections.OrderedDict()  # type: dict[str, AMSWebScenario]

        self.num_ams_file_handlers = None  # type: int
        self.AMSFileHandlers = collections.OrderedDict()  # type: dict[str, AMSFileHandler]

        self.num_ams_file_parsers = None
        self.AMSFileParsers = collections.OrderedDict()     # type: dict[str, AMSFileParser]

        self.stp_hostname = None  # type: str
        self.zabbix_proxy = None  # type: str
        self.zabbix_url = None  # type: str
        self.zabbix_retry_limit = 3  # type: int
        self.zabbix_retry_timeout = 30  # type: int
        self.zabbix_socket_timeout = 60  # type: int

        self.smoke_test_default_retry_limit = None
        self.smoke_test_default_retry_timeout = None

        self.viya_profile_name = None
        self.viya_flow_ids = None

        self.config_loaded = False

        if not self.new_config and not self.always_new_config:
            try:
                with open(self.config_path) as json_data:
                    self.raw_config = json.load(json_data, object_pairs_hook=collections.OrderedDict)
            except Exception as e:
                raise AMSConfigSyntaxException('Invalid JSON file syntax: %s' % str(e))

        # Now that we've read in the config file, let's map config to vars
        self.load()

    def get_config_dict_key(self):
        return ''

    def get_static_config_dict_key(self):
        return ''

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """
        # My config_version
        config_version_attrs = AMSConfigModelAttribute()
        config_version_attrs.set_required(True)
        config_version_attrs.set_default(self.AMSDefaults.config_version)
        config_version_attrs.set_label('Config Version')
        config_version_attrs.set_type('int')
        config_version_attrs.set_is_config_dict_key(True)
        config_version_attrs.set_allow_edit(False)
        config_version_attrs.set_hide_from_user_display(True)
        config_version_attrs.set_mapped_class_variable('config_version')
        self.config_model_attributes['config_version'] = config_version_attrs

        # Error Email Address(es)
        error_email_to_address_attrs = AMSConfigModelAttribute()
        error_email_to_address_attrs.set_required(True)
        error_email_to_address_attrs.set_default(self.AMSDefaults.email_address)
        error_email_to_address_attrs.set_label('Error email notification address(es) (separated by commas)')
        error_email_to_address_attrs.set_type('str')
        error_email_to_address_attrs.set_mapped_class_variable('error_email_to_address')
        self.config_model_attributes['error_email_to_address'] = error_email_to_address_attrs

        # Event Handler
        ams_event_handler_attrs = AMSConfigModelAttribute()
        ams_event_handler_attrs.set_required(True)
        ams_event_handler_attrs.set_default(self.AMSDefaults.event_handler)
        ams_event_handler_attrs.set_label('Event Handler')
        ams_event_handler_attrs.set_type('str')
        ams_event_handler_attrs.set_options([
            'AMSZabbix',
            'AMSEmail',
            'AMSLogger'
        ])
        ams_event_handler_attrs.set_mapped_class_variable('ams_event_handler')
        self.config_model_attributes['ams_event_handler'] = ams_event_handler_attrs

        # Incoming Dir
        incoming_dir_attrs = AMSConfigModelAttribute()
        incoming_dir_attrs.set_required(False)
        incoming_dir_attrs.set_default(self.AMSDefaults.incoming_dir)
        incoming_dir_attrs.set_label('Incoming Directory')
        incoming_dir_attrs.set_type('str')
        incoming_dir_attrs.set_mapped_class_variable('incoming_dir')
        incoming_dir_attrs.set_share_value(True)
        incoming_dir_attrs.set_return_transform('abspath')
        self.config_model_attributes['incoming_dir'] = incoming_dir_attrs

        # Archive Dir
        archive_dir_attrs = AMSConfigModelAttribute()
        archive_dir_attrs.set_required(False)
        archive_dir_attrs.set_default(self.AMSDefaults.archive_dir)
        archive_dir_attrs.set_label('Archive Directory')
        archive_dir_attrs.set_type('str')
        archive_dir_attrs.set_mapped_class_variable('archive_dir')
        archive_dir_attrs.set_share_value(True)
        archive_dir_attrs.set_return_transform('abspath')
        self.config_model_attributes['archive_dir'] = archive_dir_attrs

        # Outgoing Dir
        outgoing_dir_attrs = AMSConfigModelAttribute()
        outgoing_dir_attrs.set_required(False)
        outgoing_dir_attrs.set_default(self.AMSDefaults.outgoing_dir)
        outgoing_dir_attrs.set_label('Outgoing Directory')
        outgoing_dir_attrs.set_type('str')
        outgoing_dir_attrs.set_mapped_class_variable('outgoing_dir')
        outgoing_dir_attrs.set_share_value(True)
        outgoing_dir_attrs.set_return_transform('abspath')
        self.config_model_attributes['outgoing_dir'] = outgoing_dir_attrs

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
        debug_attrs.set_share_value(True)
        self.config_model_attributes['debug'] = debug_attrs

        # Multi Thread Max Workers
        multi_thread_max_workers_attrs = AMSConfigModelAttribute()
        multi_thread_max_workers_attrs.set_required(True)
        multi_thread_max_workers_attrs.set_default(DEFAULT_MAX_WORKERS)
        multi_thread_max_workers_attrs.set_label('Max Work Threads for Multi-Threading Module')
        multi_thread_max_workers_attrs.set_type('int')
        multi_thread_max_workers_attrs.set_mapped_class_variable('multi_thread_max_workers')
        self.config_model_attributes['multi_thread_max_workers'] = multi_thread_max_workers_attrs

        # Multi Timer Interval
        multi_thread_timer_check_interval_attrs = AMSConfigModelAttribute()
        multi_thread_timer_check_interval_attrs.set_required(True)
        multi_thread_timer_check_interval_attrs.set_default(DEFAULT_TIMER_CHECK_INTERVAL)
        multi_thread_timer_check_interval_attrs.set_label('Timer interval for Multi-Threading Module')
        multi_thread_timer_check_interval_attrs.set_type('int')
        multi_thread_timer_check_interval_attrs.set_mapped_class_variable('multi_thread_timer_check_interval')
        self.config_model_attributes['multi_thread_timer_check_interval'] = multi_thread_timer_check_interval_attrs

        # Run User
        run_user_attrs = AMSConfigModelAttribute()
        run_user_attrs.set_required(False)
        if self.AMSDefaults.default_tla:
            run_user_attrs.set_default(self.AMSDefaults.default_tla.lower() + "run")
        else:
            run_user_attrs.set_default(self.AMSDefaults.current_user)
        run_user_attrs.set_label('Run User')
        run_user_attrs.set_type('str')
        run_user_attrs.set_mapped_class_variable('run_user')
        run_user_attrs.set_share_value(True)
        self.config_model_attributes['run_user'] = run_user_attrs

        # Runbook Link
        runbook_link_attrs = AMSConfigModelAttribute()
        runbook_link_attrs.set_required(False)
        if self.AMSDefaults.default_tla:
            runbook_link_attrs.set_default(self.AMSDefaults.confluence_root + '/display/' + self.AMSDefaults.default_tla + "INT" + '/AMS+-+'+self.AMSDefaults.default_tla)
        else:
            runbook_link_attrs.set_default(None)
        runbook_link_attrs.set_label('Runbook Link')
        runbook_link_attrs.set_type('str')
        runbook_link_attrs.set_mapped_class_variable('runbook_link')
        runbook_link_attrs.set_share_value(True)
        self.config_model_attributes['runbook_link'] = runbook_link_attrs

        # Zabbix Proxy
        zabbix_proxy_attrs = AMSConfigModelAttribute()
        zabbix_proxy_attrs.set_required(False)
        zabbix_proxy_attrs.set_default(self.AMSDefaults.zabbix_proxy)
        zabbix_proxy_attrs.set_label('Zabbix proxy')
        zabbix_proxy_attrs.set_type('str')
        zabbix_proxy_attrs.set_mapped_class_variable('zabbix_proxy')
        self.config_model_attributes['zabbix_proxy'] = zabbix_proxy_attrs

        # Zabbix URL
        zabbix_url_attrs = AMSConfigModelAttribute()
        zabbix_url_attrs.set_required(False)
        zabbix_url_attrs.set_default(self.AMSDefaults.zabbix_url)
        zabbix_url_attrs.set_label('Zabbix URL')
        zabbix_url_attrs.set_type('str')
        zabbix_url_attrs.set_mapped_class_variable('zabbix_url')
        self.config_model_attributes['zabbix_url'] = zabbix_url_attrs

        # Num AMS Environments
        num_ams_environments_attrs = AMSConfigModelAttribute()
        num_ams_environments_attrs.set_required(False)
        num_ams_environments_attrs.set_default(1)
        num_ams_environments_attrs.set_label('How many environments would you like to setup?')
        num_ams_environments_attrs.set_type('int')
        num_ams_environments_attrs.set_num_required_entries(0)
        num_ams_environments_attrs.set_linked_object('Toolkit.Config.AMSEnvironment')
        num_ams_environments_attrs.set_linked_type('dict')
        num_ams_environments_attrs.set_linked_label('Environment Setup')
        num_ams_environments_attrs.set_return_map_to_variable('AMSEnvironments')
        num_ams_environments_attrs.set_mapped_class_variable('num_ams_environments')
        self.config_model_attributes['num_ams_environments'] = num_ams_environments_attrs

        # Num AMS Projects
        num_ams_projects_attrs = AMSConfigModelAttribute()
        num_ams_projects_attrs.set_required(False)
        num_ams_projects_attrs.set_default(0)
        num_ams_projects_attrs.set_label('How many projects would you like to setup?')
        num_ams_projects_attrs.set_type('int')
        num_ams_projects_attrs.set_num_required_entries(0)
        num_ams_projects_attrs.set_linked_object('Toolkit.Config.AMSProject')
        num_ams_projects_attrs.set_linked_type('dict')
        num_ams_projects_attrs.set_linked_label('Projects Setup')
        num_ams_projects_attrs.set_return_map_to_variable('AMSProjects')
        num_ams_projects_attrs.set_mapped_class_variable('num_ams_projects')
        self.config_model_attributes['num_ams_projects'] = num_ams_projects_attrs

        # Num File Routes
        num_ams_file_routes_attrs = AMSConfigModelAttribute()
        num_ams_file_routes_attrs.set_required(False)
        num_ams_file_routes_attrs.set_default(0)
        num_ams_file_routes_attrs.set_label('How many file routes would you like to setup?')
        num_ams_file_routes_attrs.set_type('int')
        num_ams_file_routes_attrs.set_num_required_entries(0)
        num_ams_file_routes_attrs.set_linked_object('Toolkit.Config.AMSFileRoute')
        num_ams_file_routes_attrs.set_linked_type('dict')
        num_ams_file_routes_attrs.set_linked_label('File Route Setup')
        num_ams_file_routes_attrs.set_return_map_to_variable('AMSFileRoutes')
        num_ams_file_routes_attrs.set_mapped_class_variable('num_ams_file_routes')
        self.config_model_attributes['num_ams_file_routes'] = num_ams_file_routes_attrs

        # Num File Handlers
        num_ams_file_handlers_attrs = AMSConfigModelAttribute()
        num_ams_file_handlers_attrs.set_required(False)
        num_ams_file_handlers_attrs.set_default(0)
        num_ams_file_handlers_attrs.set_label('How many file handlers would you like to setup?')
        num_ams_file_handlers_attrs.set_type('int')
        num_ams_file_handlers_attrs.set_num_required_entries(0)
        num_ams_file_handlers_attrs.set_linked_object('Toolkit.Config.AMSFileHandler')
        num_ams_file_handlers_attrs.set_linked_type('dict')
        num_ams_file_handlers_attrs.set_linked_label('FileHandler Setup')
        num_ams_file_handlers_attrs.set_return_map_to_variable('AMSFileHandlers')
        num_ams_file_handlers_attrs.set_mapped_class_variable('num_ams_file_handlers')
        self.config_model_attributes['num_ams_file_handlers'] = num_ams_file_handlers_attrs

        # Num File Parsers
        num_ams_file_parsers_attrs = AMSConfigModelAttribute()
        num_ams_file_parsers_attrs.set_required(False)
        num_ams_file_parsers_attrs.set_default(0)
        num_ams_file_parsers_attrs.set_label('How many file parsers would you like to define?')
        num_ams_file_parsers_attrs.set_type('int')
        num_ams_file_parsers_attrs.set_num_required_entries(0)
        num_ams_file_parsers_attrs.set_linked_object('Toolkit.Config.AMSFileParser')
        num_ams_file_parsers_attrs.set_linked_type('dict')
        num_ams_file_parsers_attrs.set_linked_label('FileParser Setup')
        num_ams_file_parsers_attrs.set_return_map_to_variable('AMSFileParsers')
        num_ams_file_parsers_attrs.set_mapped_class_variable('num_ams_file_parsers')
        self.config_model_attributes['num_ams_file_parsers'] = num_ams_file_parsers_attrs

        # Num Secrets
        num_ams_secrets_attrs = AMSConfigModelAttribute()
        num_ams_secrets_attrs.set_required(False)
        num_ams_secrets_attrs.set_default(0)
        num_ams_secrets_attrs.set_label('How many secrets would you like to setup?')
        num_ams_secrets_attrs.set_type('int')
        num_ams_secrets_attrs.set_num_required_entries(0)
        num_ams_secrets_attrs.set_linked_object('Toolkit.Config.AMSSecret')
        num_ams_secrets_attrs.set_linked_type('dict')
        num_ams_secrets_attrs.set_linked_label('Secret Setup')
        num_ams_secrets_attrs.set_return_map_to_variable('AMSSecrets')
        num_ams_secrets_attrs.set_mapped_class_variable('num_ams_secrets')
        self.config_model_attributes['num_ams_secrets'] = num_ams_secrets_attrs

        # Num MI HealthChecks
        num_ams_mihealthchecks_attrs = AMSConfigModelAttribute()
        num_ams_mihealthchecks_attrs.set_required(False)
        num_ams_mihealthchecks_attrs.set_default(0)
        num_ams_mihealthchecks_attrs.set_label('How many MI Health Checks would you like to setup?')
        num_ams_mihealthchecks_attrs.set_type('int')
        num_ams_mihealthchecks_attrs.set_num_required_entries(0)
        num_ams_mihealthchecks_attrs.set_linked_object('Toolkit.Config.AMSMIHealthCheck')
        num_ams_mihealthchecks_attrs.set_linked_type('dict')
        num_ams_mihealthchecks_attrs.set_linked_label('MI Health Checks Setup')
        num_ams_mihealthchecks_attrs.set_return_map_to_variable('AMSMIHealthChecks')
        num_ams_mihealthchecks_attrs.set_mapped_class_variable('num_ams_mihealthchecks')
        self.config_model_attributes['num_ams_mihealthchecks'] = num_ams_mihealthchecks_attrs

        # Num Web Scenarios
        num_ams_web_scenarios_attrs = AMSConfigModelAttribute()
        num_ams_web_scenarios_attrs.set_required(False)
        num_ams_web_scenarios_attrs.set_default(0)
        num_ams_web_scenarios_attrs.set_label('How many web scenarios would you like to setup?')
        num_ams_web_scenarios_attrs.set_type('int')
        num_ams_web_scenarios_attrs.set_num_required_entries(0)
        num_ams_web_scenarios_attrs.set_linked_object('Toolkit.Config.AMSWebScenario')
        num_ams_web_scenarios_attrs.set_linked_type('dict')
        num_ams_web_scenarios_attrs.set_linked_label('Web Scenarios')
        num_ams_web_scenarios_attrs.set_return_map_to_variable('AMSWebScenarios')
        num_ams_web_scenarios_attrs.set_mapped_class_variable('num_ams_web_scenarios')
        self.config_model_attributes['num_ams_web_scenarios'] = num_ams_web_scenarios_attrs

        # Num OLA Projects
        # @todo: implement OLA's
        # num_ams_olas_attrs = AMSConfigModelAttribute()
        # num_ams_olas_attrs.set_required(False)
        # num_ams_olas_attrs.set_default(1)
        # num_ams_olas_attrs.set_label('How many Operational Level Agreements (OLAs) would you like to setup?')
        # num_ams_olas_attrs.set_type('int')
        # num_ams_olas_attrs.set_num_required_entries(0)
        # num_ams_olas_attrs.set_linked_object('Toolkit.Config.AMSOla')
        # num_ams_olas_attrs.set_linked_type('dict')
        # num_ams_olas_attrs.set_linked_label('Environment Setup')
        # num_ams_olas_attrs.set_return_map_to_variable('AMSOlas')
        # num_ams_olas_attrs.set_mapped_class_variable('num_ams_olas')
        # self.config_model_attributes['num_ams_olas'] = num_ams_olas_attrs

        # STP Hostname
        stp_hostname_attrs = AMSConfigModelAttribute()
        stp_hostname_attrs.set_required(False)
        stp_hostname_attrs.set_default(None)
        stp_hostname_attrs.set_label('STP Hostname?')
        stp_hostname_attrs.set_type('str')
        stp_hostname_attrs.set_mapped_class_variable('stp_hostname')
        stp_hostname_attrs.set_share_value(False)
        stp_hostname_attrs.set_hide_from_user_display(True)
        self.config_model_attributes['stp_hostname'] = stp_hostname_attrs

        # SmokeTest Defaults
        smoke_test_default_retry_limit_attrs = AMSConfigModelAttribute()
        smoke_test_default_retry_limit_attrs.set_required(True)
        smoke_test_default_retry_limit_attrs.set_default(self.AMSDefaults.smoke_test_default_retry_limit)
        smoke_test_default_retry_limit_attrs.set_hide_from_user_display(True)
        smoke_test_default_retry_limit_attrs.set_type('int')
        smoke_test_default_retry_limit_attrs.set_mapped_class_variable('smoke_test_default_retry_limit')
        self.config_model_attributes['smoke_test_default_retry_limit'] = smoke_test_default_retry_limit_attrs

        smoke_test_default_retry_timeout_attrs = AMSConfigModelAttribute()
        smoke_test_default_retry_timeout_attrs.set_required(True)
        smoke_test_default_retry_timeout_attrs.set_default(self.AMSDefaults.smoke_test_default_retry_timeout)
        smoke_test_default_retry_timeout_attrs.set_hide_from_user_display(True)
        smoke_test_default_retry_timeout_attrs.set_type('int')
        smoke_test_default_retry_timeout_attrs.set_mapped_class_variable('smoke_test_default_retry_timeout')
        self.config_model_attributes['smoke_test_default_retry_timeout'] = smoke_test_default_retry_timeout_attrs

        return True

    def load(self):
        """

        :return:
        :rtype:
        """
        try:
            self._read_config_version()
            self._read_zabbix_proxy()
            self._read_zabbix_url()
            self._read_error_email_to_address()
            self._read_ams_event_handler()
            self._read_incoming_dir()
            self._read_archive_dir()
            self._read_outgoing_dir()
            self._read_debug()
            self._read_environments()
            self._read_multi_thread_max_workers()
            self._read_multi_thread_timer_check_interval()
            self._read_run_user()
            self._read_runbook_link()
            self._read_projects()
            self._read_file_routes()
            self._read_secrets()
            self._read_healthchecks()
            self._read_web_scenarios()
            self._read_file_handlers()
            self._read_file_parsers()
            self._read_stp_hostname()
            self._read_smoke_test_defaults()
            self.config_loaded = True
            self._read_int('zabbix_retry_limit')
            self._read_int('zabbix_retry_timeout')
            self._read_int('zabbix_socket_timeout')
            self._read_string('viya_profile_name')
            self._read_string('viya_flow_ids')
            # @todo: need to handle dynamic variables somehow.  Potentially a V2 enhancement.
        except (AMSConfigException, AMSEnvironmentException, AMSJibbixOptionsException, AMSLogFileException, AMSOlaException, AMSProjectException, AMSScheduleException):
            raise
        except Exception as e:
            raise AMSConfigException(e)

    def _read_config_version(self):
        """
        This method will set the config_version in the 'global' section of the AMS Config.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'config_version' in self.raw_config and self.raw_config['config_version']:
            self.config_version = str(self.raw_config['config_version']).strip()
        else:
            self.config_version = self.AMSDefaults.config_version
            self.AMSLogger.debug('config_version is not set in config.  Going to set to ' + str(self.config_version) + ' based off of global default')

        return True

    def _read_error_email_to_address(self):
        """
        This method will set the error email address in the 'global' section of the AMS Config.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'error_email_to_address' in self.raw_config and self.raw_config['error_email_to_address']:
            self.error_email_to_address = str(self.raw_config['error_email_to_address']).strip()
        else:
            self.error_email_to_address = self.AMSDefaults.email_address
            self.AMSLogger.debug('error_email_to_address is not set in config.  Going to set to ' + self.error_email_to_address + ' based off of global default')

        return True

    def _read_zabbix_proxy(self):
        """
        This method will set the zabbix_proxy in the 'global' section of the AMS Config.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'zabbix_proxy' in self.raw_config and self.raw_config['zabbix_proxy']:
            self.zabbix_proxy = str(self.raw_config['zabbix_proxy']).strip()
        else:
            self.zabbix_proxy = self.AMSDefaults.zabbix_proxy
            self.AMSLogger.debug('zabbix_proxy is not set in config.  Going to set to ' + self.zabbix_proxy + ' based off of global default')

        return True

    def _read_zabbix_url(self):
        """
        This method will set the zabbix_url in the 'global' section of the AMS Config.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'zabbix_url' in self.raw_config and self.raw_config['zabbix_url']:
            self.zabbix_url = str(self.raw_config['zabbix_url']).strip()
        else:
            self.zabbix_url = self.AMSDefaults.zabbix_url
            self.AMSLogger.debug('zabbix_url is not set in config.  Going to set to ' + self.zabbix_url + ' based off of global default')

        return True

    def _read_ams_event_handler(self):
        """
        This method will set the AMS Event Handler in the 'global' section of the AMS Config.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'ams_event_handler' in self.raw_config and self.raw_config['ams_event_handler']:
            self.ams_event_handler = str(self.raw_config['ams_event_handler']).strip()
        else:
            self.ams_event_handler = self.AMSDefaults.event_handler
            self.AMSLogger.debug('ams_event_handler is not set in config.  Going to set to ' + self.ams_event_handler + ' based off of global default')

        return True

    def _read_incoming_dir(self):
        """
        This method will set the incoming directory in the 'global' section of the AMS Config.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'incoming_dir' in self.raw_config and self.raw_config['incoming_dir']:
            self.incoming_dir = str(self.raw_config['incoming_dir']).strip()
        else:
            self.incoming_dir = self.AMSDefaults.incoming_dir
            self.AMSLogger.debug('incoming_dir is not set in config.  Going to set to ' + self.incoming_dir + ' based off of global default')

        if not self.fev.directory_readable(self.incoming_dir):
            self.AMSLogger.critical('Incoming directory does not exist or is not readable: ' + self.incoming_dir)
            return False

        return True

    def _read_archive_dir(self):
        """
        This method will set the environment dictionary from the config file.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'archive_dir' in self.raw_config and self.raw_config['archive_dir']:
            self.archive_dir = str(self.raw_config['archive_dir']).strip()
        else:
            self.archive_dir = self.AMSDefaults.archive_dir
            self.AMSLogger.debug('archive_dir is not set in config.  Going to set to ' + self.archive_dir + ' based off of global default')

        if not self.fev.directory_readable(self.archive_dir):
            self.AMSLogger.critical('Archive directory does not exist or is not readable: ' + self.archive_dir)
            return False

        return True

    def _read_outgoing_dir(self):
        """
        This method will set the archive directory in the 'global' section of the AMS Config.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'outgoing_dir' in self.raw_config and self.raw_config['outgoing_dir']:
            self.outgoing_dir = str(self.raw_config['outgoing_dir']).strip()
        else:
            self.outgoing_dir = self.AMSDefaults.outgoing_dir
            self.AMSLogger.debug('outgoing_dir is not set in config.  Going to set to ' + self.outgoing_dir + ' based off of global default')

        if not self.fev.directory_readable(self.outgoing_dir):
            self.AMSLogger.critical('Outgoing directory does not exist or is not readable: ' + self.outgoing_dir)
            return False

        return True

    def _read_environments(self):
        """
        This method will set the environments dictionary of AMSEnvironment objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.num_ams_environments = 0
        if 'environments' in self.raw_config and self.raw_config['environments'] and isinstance(self.raw_config['environments'], dict):
            for hostname, environment_data in self.raw_config['environments'].iteritems():
                self.num_ams_environments += 1
                ams_environment = AMSEnvironment(self.new_config)
                ams_environment.load(hostname, environment_data)
                self.AMSEnvironments[hostname] = ams_environment
        else:
            if not self.new_config:
                self.AMSLogger.debug('No environments set in config.')
            else:
                self.AMSLogger.info('No environments set in the config.')
            return False

        return True

    def get_my_environment(self):
        """
        This method returns an AMSEnvironment object of the current 'environment (server)' that the script is running on.
        :return: AMSEnvironment object
        :rtype: AMSEnvironment
        """
        try:
            return self.AMSEnvironments[self.my_hostname]
        except Exception as e:
            if self.new_config:
                self.AMSLogger.debug('No environments are configured as this is a new config.')
                return AMSEnvironment(self.new_config)
            else:
                if self.AMSDefaults.is_dev_host():
                    return AMSEnvironment(self.new_config)
                else:
                    raise AMSConfigException('Could not determine my environment from my hostname: ' + str(self.my_hostname) + ".\n" + str(e))

    def _read_multi_thread_max_workers(self):
        """
        This method will set the multi_thread_max_workers variable for the environment.  If not defined, it will set it based off the environment object.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'multi_thread_max_workers' in self.raw_config and self.raw_config['multi_thread_max_workers']:
            self.multi_thread_max_workers = int(self.raw_config['multi_thread_max_workers'])
        else:
            self.multi_thread_max_workers = DEFAULT_MAX_WORKERS
            self.AMSLogger.debug('multi_thread_max_workers is not set in config.  Going to set to %s based off of global default' % self.multi_thread_max_workers)

        return True

    def _read_multi_thread_timer_check_interval(self):
        """
        This method will set the multi_thread_timer_check_interval variable for the environment.  If not defined, it will set it based off the environment object.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'multi_thread_timer_check_interval' in self.raw_config and self.raw_config['multi_thread_timer_check_interval']:
            self.multi_thread_timer_check_interval = int(self.raw_config['multi_thread_timer_check_interval'])
        else:
            self.multi_thread_timer_check_interval = DEFAULT_TIMER_CHECK_INTERVAL
            self.AMSLogger.debug('multi_thread_timer_check_interval is not set in config.  Going to set to %s based off of global default' % self.multi_thread_timer_check_interval)

        return True

    def _read_run_user(self):
        """
        This method will set the run_user variable for the environment.  If not defined, it will set it based off the environment object.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'run_user' in self.raw_config and self.raw_config['run_user']:
            self.run_user = str(self.raw_config['run_user']).strip()
        else:
            try:
                self.AMSLogger.debug('run_user is not set in config.  Going to try and set based off of my environment object.')
                self._set_run_user_from_my_environment()
            except AMSConfigException:
                if self.new_config:
                    self.AMSLogger.info('No run_user set in config or environment as this is a new config.')
                else:
                    self.AMSLogger.debug('No run_user set in config or environment.')
                return False

        return True

    def _set_run_user_from_my_environment(self):
        """
        This method will set the run_user variable from the environment object.  If not defined, it will set it based off the environment object.
        :return: True upon success or exception upon failure.
        :rtype: bool
        """
        my_environment = self.get_my_environment()
        if my_environment.run_user:
            self.run_user = my_environment.run_user
        elif not my_environment.read_run_user():
            if not self.new_config:
                raise AMSConfigException('run_user required.  Not defined in global config or in the environments config section, nor could it be set from the TLA.')

            self.AMSLogger.debug('run_user not defined in global config or in the environments config section, nor could it be set from the TLA.')
            return False
        else:
            if not self.new_config:
                raise AMSConfigException('run_user required.  Not defined in global config or in the environments config section')

            self.AMSLogger.debug('run_user not defined in global config or in the environments config section.')
            return False

    def _read_runbook_link(self):
        """
        This method will set the runbook_link variable for the environment.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'runbook_link' in self.raw_config and self.raw_config['runbook_link']:
            self.runbook_link = str(self.raw_config['runbook_link']).strip()
        else:
            self.AMSLogger.debug('runbook_link is not set in config.')
            return False

        return True

    def _read_projects(self):
        """
        This method will set the projects dictionary of AMSProject objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.num_ams_projects = 0
        if 'projects' in self.raw_config and self.raw_config['projects'] and isinstance(self.raw_config['projects'], dict):
            for project_name, project_data in self.raw_config['projects'].iteritems():
                self.num_ams_projects += 1
                ams_project = AMSProject()
                ams_project.load(project_name, project_data)
                self.AMSProjects[project_name] = ams_project

        else:
            self.AMSLogger.debug('No projects set in config.')
            return False

        return True

    def _read_file_routes(self):
        """
        This method will set the file route dictionary of AMSFileRoute objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.num_ams_file_routes = 0
        if 'file_routes' in self.raw_config and self.raw_config['file_routes'] and isinstance(self.raw_config['file_routes'], dict):
            for file_route_name, file_route_data in self.raw_config['file_routes'].iteritems():
                self.num_ams_file_routes += 1
                ams_file_route = AMSFileRoute()
                ams_file_route.load(file_route_name, file_route_data)
                self.AMSFileRoutes[file_route_name] = ams_file_route

        else:
            self.AMSLogger.debug('No file routes set in config.')
            return False

        return True

    def _read_secrets(self):
        """
        This method will set the secrets dictionary of AMSSecret objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.num_ams_secrets = 0
        if 'secrets' in self.raw_config and self.raw_config['secrets'] and isinstance(self.raw_config['secrets'], dict):
            for ams_secret_name, ams_secret_data in self.raw_config['secrets'].iteritems():
                self.num_ams_secrets += 1
                try:
                    ams_secret = AMSSecret()
                    ams_secret.load(ams_secret_name, ams_secret_data)
                    self.AMSSecrets[ams_secret_name] = ams_secret
                except Exception as e:
                    import traceback
                    self.AMSLogger.critical(str(e))
                    self.AMSLogger.critical(traceback.format_exc())

        else:
            if self.new_config:
                self.AMSLogger.info('No secrets set in config.')
            else:
                self.AMSLogger.debug('No secrets set in config.')
            return False

        return True

    def _read_healthchecks(self):
        """
        This method will set the healthcheck dictionary of AMSMIHealthCheck objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.num_ams_mihealthchecks = 0
        if 'mi_healthchecks' in self.raw_config and self.raw_config['mi_healthchecks'] and isinstance(self.raw_config['mi_healthchecks'], dict):
            for healthcheck_name, healthcheck_data in self.raw_config['mi_healthchecks'].iteritems():
                self.num_ams_mihealthchecks += 1
                healthcheck = AMSMIHealthCheck()
                healthcheck.load(healthcheck_name, healthcheck_data)
                self.AMSMIHealthChecks[healthcheck_name] = healthcheck

        else:
            if self.new_config:
                self.AMSLogger.info('No mi health checks set in config.')
            else:
                self.AMSLogger.debug('No mi health checks set in config.')
            return False

        return True

    def _read_web_scenarios(self):
        """
        This method will set the projects dictionary of AMSWebScenario objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.num_ams_web_scenarios = 0
        if 'web_scenarios' in self.raw_config and self.raw_config['web_scenarios'] and isinstance(self.raw_config['web_scenarios'], dict):
            for name, data in self.raw_config['web_scenarios'].iteritems():
                self.num_ams_web_scenarios += 1
                web_scenario = AMSWebScenario()
                web_scenario.load(name, data)
                self.AMSWebScenarios[name] = web_scenario

        else:
            self.AMSLogger.debug('No web scenarios set in config.')
            return False

        return True

    def _read_file_handlers(self):
        """
        This method will set the projects dictionary of AMSFileHandler objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.num_ams_file_handlers = 0
        if 'file_handlers' in self.raw_config and self.raw_config['file_handlers'] and isinstance(self.raw_config['file_handlers'], dict):
            for file_handler_name, config_data in self.raw_config['file_handlers'].iteritems():
                self.num_ams_file_handlers += 1
                from pydoc import locate
                file_handler = locate('Toolkit.Config.AMSFileHandler')()
                file_handler.load(file_handler_name, config_data)
                self.AMSFileHandlers[file_handler_name] = file_handler

        else:
            self.AMSLogger.debug('No file handlers set in config.')
            return False

        return True

    def _read_file_parsers(self):
        """
        This method will set the projects dictionary of AMSFileParserobjects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.num_ams_file_parsers = 0
        if 'file_parsers' in self.raw_config and self.raw_config['file_parsers'] and isinstance(self.raw_config['file_parsers'], dict):
            for file_parser_name, config_data in self.raw_config['file_parsers'].iteritems():
                self.num_ams_file_parsers += 1
                from pydoc import locate
                file_parser = locate('Toolkit.Config.AMSFileParser')()
                file_parser.load(file_parser_name, config_data)
                self.AMSFileParsers[file_parser_name] = file_parser

        else:
            self.AMSLogger.debug('No file parsers set in config.')
            return False

    def _read_stp_hostname(self):
        """
        This method will set the stp_hostname in the 'global' section of the AMS Config.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'stp_hostname' in self.raw_config and self.raw_config['stp_hostname']:
            self.stp_hostname = str(self.raw_config['stp_hostname']).strip()
        else:
            self.AMSLogger.debug('Hostname is not set')
            return False

        return True

    def _read_smoke_test_defaults(self):
        if 'smoke_test_default_retry_limit' in self.raw_config and self.raw_config['smoke_test_default_retry_limit']:
            self.smoke_test_default_retry_limit = int(self.raw_config['smoke_test_default_retry_limit'])
        else:
            self.smoke_test_default_retry_limit = self.AMSDefaults.smoke_test_default_retry_limit

        if 'smoke_test_default_retry_timeout' in self.raw_config and self.raw_config['smoke_test_default_retry_timeout']:
            self.smoke_test_default_retry_timeout = int(self.raw_config['smoke_test_default_retry_timeout'])
        else:
            self.smoke_test_default_retry_timeout = self.AMSDefaults.smoke_test_default_retry_timeout

        return True

    def write_config(self):

        if not self.valid_config:
            self.AMSLogger.debug('No config file is used, so not writing config file')
        else:
            try:
                self.new_raw_config = self._write_config_section(self.new_raw_config)
                if cmp(self.new_raw_config, self.raw_config) == 0:
                    self.AMSLogger.debug('New config and old config are the same - no need to write a new config file.')
                else:
                    self.backup_config()
                    self._write_new_config_to_disk()
            except Exception:
                # @todo: handle exceptions appropriately
                raise

            print json.dumps(self.new_raw_config, indent=4)

    def backup_config(self):
        # os.makedirs(self.backup_folder)

        if self.new_config:
            return True

        if not self.fev.directory_exists(self.backup_config_dir):
            try:
                os.makedirs(self.backup_config_dir)
            except Exception as e:
                raise AMSConfigException('Could not create backup folder - did not save changes: ' + str(e))

        if not self.fev.directory_writeable(self.backup_config_dir):
            raise AMSConfigException('Backup config directory is not writeable: %s' % self.backup_config_dir)

        try:
            cur_config_file_name = os.path.basename(self.config_path)
            backup_config_file_name = cur_config_file_name + '_' + str(datetime.datetime.today().strftime('%Y%m%d_%H%M%S'))
            shutil.copy(self.config_path, os.path.join(self.backup_config_dir, backup_config_file_name))
            return True
        except Exception as e:
            raise AMSConfigException('Could not create backup of current config file - did not save changes: ' + str(e))

    def _write_new_config_to_disk(self):
        if not self.fev.directory_writeable(self.config_dir):
            raise AMSConfigException('Config directory is not writeable: %s' % self.config_dir)

        try:
            fh = open(self.config_path, "w")
            fh.write(json.dumps(self.new_raw_config, indent=2))
            fh.close()
            return True
        except Exception as e:
            raise AMSConfigException('Failed to save config file: ' + str(e))

    @staticmethod
    def get_default_config_path():
        """
        This method will return the default config path for the AMS config file.
        :return: Returns the absolute path of the AMS Config file.
        :rtype: str
        """
        return os.path.abspath(DEFAULT_CONFIG_PATH)

    @staticmethod
    def get_default_outgoing_dir():
        """
        This method will return the default config path for the outgoing directory.
        :return: Returns the absolute path of the outgoing directory.
        :rtype: str
        """
        return os.path.abspath(locate('Toolkit.Lib.Defaults.AMSDefaults')().outgoing_dir)

    @staticmethod
    def get_default_incoming_dir():
        """
        This method will return the default config path for the incoming directory.
        :return: Returns the absolute path of the incoming directory.
        :rtype: str
        """
        return os.path.abspath(locate('Toolkit.Lib.Defaults.AMSDefaults')().incoming_dir)

    @staticmethod
    def get_default_archive_dir():
        """
        This method will return the default config path for the archive directory.
        :return: Returns the absolute path of the archive directory.
        :rtype: str
        """
        return os.path.abspath(locate('Toolkit.Lib.Defaults.AMSDefaults')().archive_dir)

    def get_file_route_by_name(self, file_route_name):
        """
        This method will take a file route name and return the AMSFileRoute object associated with the name.
        :param file_route_name: The file route name you wish to retrieve the config object for.
        :type file_route_name: str
        :return: Returns the AMSFileRoute config object.
        :rtype: AMSFileRoute
        """
        tmp_file_route_name = str(file_route_name).strip()
        if not tmp_file_route_name:
            raise AMSConfigException('file_route_name required in get_file_route_by_name.')

        if tmp_file_route_name not in self.AMSFileRoutes:
            raise AMSConfigException('%s is not a file route that exists in the current config.' % tmp_file_route_name)

        return self.AMSFileRoutes[tmp_file_route_name]

    def get_environment_by_name(self, environment_name):
        """
        This method will take an environment name and return the AMSEnvironment object associated with the name.
        :param environment_name: The file route name you wish to retrieve the config object for.
        :type environment_name: str
        :return: Returns the AMSEnvironment config object.
        :rtype: AMSEnvironment
        """
        tmp_environment_name = str(environment_name).strip()
        if not tmp_environment_name:
            raise AMSConfigException('environment_name required in get_environment_by_name.')

        if tmp_environment_name not in self.AMSEnvironments:
            raise AMSConfigException('%s is not an environment that exists in the current config.' % tmp_environment_name)

        return self.AMSEnvironments[tmp_environment_name]

    def get_file_handler_by_name(self, file_handler_name):
        """
        This method will take a file handler name and return the AMSFileHandler object associated with the name.
        :param file_handler_name: The file handler name you wish to retrieve the config object for.
        :type file_handler_name: str
        :return: Returns the AMSFileHandler config object.
        :rtype: AMSFileHandler
        """
        tmp_file_handler_name = str(file_handler_name).strip()
        if not tmp_file_handler_name:
            raise AMSConfigException('file_handler_name required in get_file_handler_by_name.')

        if tmp_file_handler_name not in self.AMSFileHandlers:
            raise AMSConfigException('%s is not a file handler that exists in the current config.' % tmp_file_handler_name)

        return self.AMSFileHandlers[tmp_file_handler_name]

    def get_file_parser_by_name(self, file_parser_name):
        tmp_file_parser_name = str(file_parser_name).strip()
        if not tmp_file_parser_name:
            raise AMSConfigException('file_parser_name is required for get_file_parser_by_name.')

        return self.AMSFileParsers[tmp_file_parser_name]

    def get_schedule_by_name(self, schedule_name, project_name=None):
        """
        This method will take a schedule name and return the AMSSchedule object associated with the name.
        :param schedule_name: The schedule name you wish to retrieve the config object for.
        :type schedule_name: str
        :param project_name: The project name you wish to retrieve the config object for.
        :type project_name: str
        :return: Returns the AMSSchedule config object.
        :rtype: AMSSchedule
        """
        tmp_schedule_name = str(schedule_name).strip()
        if not tmp_schedule_name:
            raise AMSConfigException('schedule_name required in get_schedule_by_name.')

        if len(self.AMSProjects) < 1:
            raise AMSConfigException('The current config has no projects defined.  Schedules require projects to be defined.  Please setup a project first.')

        if not project_name:
            for project, ams_project_obj in self.AMSProjects.iteritems():  # type: str, AMSProject
                if len(ams_project_obj.AMSSchedules) < 1:
                    self.AMSLogger.debug('The current project, %s, has no schedules defined.  Please setup a schedule in this project.' % project)
                    continue

                if tmp_schedule_name not in ams_project_obj.AMSSchedules:
                    self.AMSLogger.debug('%s is not a schedule that exists in the current config within the %s project.' % (tmp_schedule_name, project))
                else:
                    return ams_project_obj.AMSSchedules[schedule_name]
        else:
            if project_name not in self.AMSProjects:
                self.AMSLogger.debug('The project, %s, has no schedules defined.  Please setup a schedule in this project.' % project_name)
            else:
                ams_project_obj = self.AMSProjects[project_name]
                if tmp_schedule_name not in ams_project_obj.AMSSchedules:
                    self.AMSLogger.debug('%s is not a schedule that exists in the current config within the %s project.' % (tmp_schedule_name, project_name))
                else:
                    return ams_project_obj.AMSSchedules[tmp_schedule_name]

        raise AMSScheduleException('Could not locate %s schedule in any defined projects in the current config.' % tmp_schedule_name)

    def get_secret_by_name(self, secret_name):
        """
        This method will take a secret name and return the AMSSecret object associated with the name.
        :param secret_name: The file route name you wish to retrieve the config object for.
        :type secret_name: str
        :return: Returns the AMSSecret config object.
        :rtype: AMSSecret
        """
        tmp_secret_name = str(secret_name).strip()
        if not tmp_secret_name:
            raise AMSConfigException('secret_name required in get_secret_by_name.')

        if tmp_secret_name not in self.AMSSecrets:
            raise AMSConfigException('%s is not a secret that exists in the current config.' % tmp_secret_name)

        return self.AMSSecrets[tmp_secret_name]

    def get_secret_by_env_type(self):
        """
        Returns a list of AMSSecret objects that matches the environment type of the host at runtime.
        :return: Returns the AMSSecret config objects.
        :rtype: List AMSSecret
        """
        my_environment = self.get_my_environment()

        env_type = my_environment.env_type

        try:
            secrets = list(filter(lambda secret: env_type.upper() in secret.environment.upper(), self.AMSSecrets.values()))
            if len(secrets) == 0:
                self.AMSLogger.info('No secrets found for env {}'.format(env_type.upper()))
        except AttributeError as e:
            self.AMSLogger.debug('Env_type may not be defined.\n{}'.format(str(e)))
        return secrets

    def get_healthcheck_by_name(self, healthcheck_name):
        """
        This method will take a health check_name and return the AMSMIHealthCheck object associated with the name.
        :param healthcheck_name: The file route name you wish to retrieve the config object for.
        :type healthcheck_name: str
        :return: Returns the AMSMIHealthCheck config object.
        :rtype: AMSMIHealthCheck
        """
        tmp_healthcheck_name = str(healthcheck_name).strip()
        if not tmp_healthcheck_name:
            raise AMSConfigException('healthcheck_name required in get_healthcheck_by_name.')

        if tmp_healthcheck_name not in self.AMSMIHealthChecks:
            raise AMSConfigException('%s is not a healthcheck that exists in the current config.' % tmp_healthcheck_name)

        return self.AMSMIHealthChecks[tmp_healthcheck_name]

    def get_web_scenario_by_name(self, web_scenario_name):
        """
        This method will take a web_scenario_name name and return the AMSWebScenario object associated with the name.
        :param web_scenario_name: The web scenario name you wish to retrieve the config object for.
        :type web_scenario_name: str
        :return: Returns the AMSWebScenario config object.
        :rtype: AMSWebScenario
        """
        tmp_web_scenario_name = str(web_scenario_name).strip()
        if not tmp_web_scenario_name:
            raise AMSConfigException('web_scenario_name required in get_web_scenario_by_name.')

        if tmp_web_scenario_name not in self.AMSWebScenarios:
            raise AMSConfigException('%s is not a web scenario that exists in the current config.' % tmp_web_scenario_name)

        return self.AMSWebScenarios[tmp_web_scenario_name]

    def get_all_schedules(self):
        """
        This method will return a dict of all schedules within all projects
        :return: A dictionary of schedule data for all schedules
        :rtype: dict
        """

        if len(self.AMSProjects) < 1:
            raise AMSConfigException('The current config has no projects defined.  Schedules require projects to be defined.  Please setup a project first.')

        ret_schedules = {}
        for project_name, ams_project_obj in self.AMSProjects.iteritems():  # type: str, AMSProject
            if len(ams_project_obj.AMSSchedules) < 1:
                self.AMSLogger.debug('The current project, %s, has no schedules defined.  Please setup a schedule in this project.' % project_name)
                continue

            for schedule_name, ams_schedule_obj in ams_project_obj.AMSSchedules.iteritems():  # type: str, AMSSchedule
                ret_schedules[project_name + '::' + schedule_name] = {
                    'project_name': project_name,
                    'schedule_name': schedule_name,
                    'project_obj': ams_project_obj,
                    'schedule_obj': ams_schedule_obj
                }

        return ret_schedules

    def get_one_schedule_for_lld(self, ad_hok_schedule):
        """
        This method will return a dict of the one schedule that is passed in
        :return: A dictionary of schedule data for a single schedule
        :rtype: dict
        """

        if len(self.AMSProjects) < 1:
            raise AMSConfigException('The current config has no projects defined.  Schedules require projects to be defined.  Please setup a project first.')

        ret_schedules = {}
        for project_name, ams_project_obj in self.AMSProjects.iteritems():  # type: str, AMSProject
            if len(ams_project_obj.AMSSchedules) < 1:
                self.AMSLogger.debug('The current project, %s, has no schedules defined.  Please setup a schedule in this project.' % project_name)
                continue

            for schedule_name, ams_schedule_obj in ams_project_obj.AMSSchedules.iteritems():  # type: str, AMSSchedule
                if schedule_name == ad_hok_schedule:
                    ret_schedules[project_name + '::' + schedule_name] = {
                        'project_name': project_name,
                        'schedule_name': schedule_name,
                        'project_obj': ams_project_obj,
                        'schedule_obj': ams_schedule_obj
                    }
        return ret_schedules

    def get_runbook_link_for_schedule(self, schedule_name):
        """
        This method will take a schedule name and return the runbook link associated with that schedule, or the one associated with the main config.
        :param schedule_name: The schedule name you wish to retrieve the config object for.
        :type schedule_name: str
        :return: Returns the string for the runbook link or ''.
        :rtype: str
        """
        runbook_link = ''
        tmp_schedule_name = str(schedule_name).strip()
        if not tmp_schedule_name:
            raise AMSConfigException('schedule_name required in get_schedule_by_name.')

        if len(self.AMSProjects) > 0:
            for project_name, ams_project_obj in self.AMSProjects.iteritems():  # type: str, AMSProject
                if len(ams_project_obj.AMSSchedules) < 1:
                    self.AMSLogger.debug('The current project, %s, has no schedules defined.  Please setup a schedule in this project.' % project_name)
                    continue

                if tmp_schedule_name not in ams_project_obj.AMSSchedules:
                    self.AMSLogger.debug('%s is not a schedule that exists in the current config within the %s project.' % (tmp_schedule_name, project_name))
                else:
                    runbook_link = ams_project_obj.AMSSchedules[schedule_name].runbook_sub_link

        if not runbook_link and self.runbook_link:
            runbook_link = self.runbook_link

        return runbook_link

    def get_adhoc_schedule_object(self):
        """
        This method will return a AMSSchedule object with defaults loaded up for an 'ad-hoc' schedule.
        :return: A defaults loaded AMSSchedule object.
        :rtype: AMSSchedule
        """

        my_environment = self.get_my_environment()
        ams_schedule = AMSSchedule()
        ams_schedule.schedule_name = self.AMSDefaults.default_adhoc_schedule_name
        ams_schedule.project_name = self.AMSDefaults.default_adhoc_project_name
        if my_environment.tla:
            ams_schedule.tla = my_environment.tla
        else:
            ams_schedule.tla = self.AMSDefaults.AMSJibbixOptions.project
        if my_environment.run_user:
            ams_schedule.home_dir = os.path.join('/', ams_schedule.tla.lower(), 'projects', 'default', my_environment.run_user)
        else:
            ams_schedule.home_dir = os.path.join('/', ams_schedule.tla.lower(), 'projects', 'default', self.AMSDefaults.current_user)
        ams_schedule.signal_dir = os.path.join(ams_schedule.home_dir, 'signals')
        ams_schedule.sso_run_path = self.AMSDefaults.default_sso_run_path
        ams_schedule.automation_type = self.AMSDefaults.default_automation_type
        ams_schedule.AMSJibbixOptions = self.AMSDefaults.AMSJibbixOptions

        return ams_schedule

    def get_incoming_directory_by_schedule_name(self, schedule_name):
        """

        :param schedule_name:
        :type : str
        :return: Returns the incoming directory defined in a schedule
        :rtype: str
        """
        if len(self.AMSProjects) < 1:
            return self.incoming_dir

        for project_name, ams_project_obj in self.AMSProjects.iteritems():  # type: str, AMSProject
            if len(ams_project_obj.AMSSchedules) < 1:
                continue

            for schedule, ams_schedule_obj in ams_project_obj.AMSSchedules.iteritems():  # type: str, AMSSchedule
                if schedule == schedule_name and ams_schedule_obj.incoming_dir:
                    return ams_schedule_obj.incoming_dir
        self.AMSLogger.critical('Error: Incoming directory not defined in schedule %s' % schedule_name)
        raise AMSConfigException(
            'The current config has no schedule with name ' + schedule_name + ' defined')

    def get_signal_directory_by_schedule_name(self, schedule_name):
        """

        :param schedule_name:
        :type : str
        :return: Returns the signal directory that is to be used for a schedule
        :rtype: str
        """
        for project_name, ams_project_obj in self.AMSProjects.iteritems():  # type: str, AMSProject
            if len(ams_project_obj.AMSSchedules) < 1:
                continue

            for schedule, ams_schedule_obj in ams_project_obj.AMSSchedules.iteritems():  # type: str, AMSSchedule
                if schedule == schedule_name:
                    if len(ams_schedule_obj.signal_dir) > 0:
                        return ams_schedule_obj.signal_dir
                    else:  # see if the project has the signal directory defined
                        if len(ams_project_obj.signal_dir) > 0:
                            return ams_project_obj.signal_dir

        self.AMSLogger.critical('Error: Signal directory not defined in schedule %s' % schedule_name)
        raise AMSConfigException(
            'The current config has no schedule with name ' + schedule_name + ' defined')


    def get_one_route_for_lld(self, route):
        """
        This method will return a dict of the one schedule that is passed in
        :return: A dictionary of schedule data for a single schedule
        :rtype: dict
        """

        ret_routes = {}

        for route_name, ams_route_obj in self.AMSFileRoutes.iteritems():
            if route_name == route:
                ret_routes[route_name] = {
                    'route_name': route_name,
                    'route_obj': ams_route_obj
                }

        return ret_routes


    def get_all_routes(self):
        """
        This method will return a dict of all file routes
        :return: A dictionary of file route data for all file routes
        :rtype: dict
        """

        ret_routes = {}

        for route_name, ams_route_obj in self.AMSFileRoutes.iteritems():
            ret_routes[route_name] = {
                'route_name': route_name,
                'route_obj': ams_route_obj
            }

        return ret_routes

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass

    def _validate_incoming_dir(self, tmp_input):
        # self.AMSLogger.debug("Incoming Dir validator")
        return self._ams_validate_directory(tmp_input)

    def _validate_archive_dir(self, tmp_input):
        return self._ams_validate_directory(tmp_input)

    def _validate_outgoing_dir(self, tmp_input):
        return self._ams_validate_directory(tmp_input)

    def _validate_error_email_to_address(self, tmp_input):
        return self._ams_validate_email(tmp_input)

    def _validate_runbook_link(self, tmp_input):
        if len(tmp_input) == 0:
            return True
        return self._ams_validate_url(tmp_input)
