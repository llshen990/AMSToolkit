import os, sys, collections
from pydoc import locate

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSJibbixOptions, AMSFileRouteMethod, AbstractAMSConfig, AMSConfigModelAttribute, AMSCommentable
from Toolkit.Exceptions import AMSMethodException

class AMSFileRoute(AMSCommentable):

    def __init__(self):
        self.AMSDefaults = locate('Toolkit.Lib.Defaults.AMSDefaults')()
        AMSCommentable.__init__(self)
        self.raw_config = collections.OrderedDict()
        self.file_route_name = None  # type: str
        self.polling_interval = None  # type: int
        self.retry_limit = None  # type: int
        self.retry_wait = None  # type: int
        self.dependency_check_policy = None
        self.AMSJibbixOptions = AMSJibbixOptions()
        self.AMSFileRouteMethod = AMSFileRouteMethod()
        self.num_ams_dependency_checkers = None  # type: int
        self.AMSDependencyChecks = collections.OrderedDict()  # type: dict[str, AMSDependencyChecker]

    def get_config_dict_key(self):
        return self.file_route_name

    def get_static_config_dict_key(self):
        return 'file_routes'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # File Route Name
        file_route_name_attrs = AMSConfigModelAttribute()
        file_route_name_attrs.set_required(True)
        file_route_name_attrs.set_default(None)
        file_route_name_attrs.set_label('File Route Name')
        file_route_name_attrs.set_type('str')
        file_route_name_attrs.set_is_config_dict_key(True)
        file_route_name_attrs.set_mapped_class_variable('file_route_name')
        self.config_model_attributes['file_route_name'] = file_route_name_attrs

        # Polling Interval
        polling_interval_attrs = AMSConfigModelAttribute()
        polling_interval_attrs.set_required(False)
        polling_interval_attrs.set_default(-1)
        polling_interval_attrs.set_label('Polling Interval')
        polling_interval_attrs.set_type('int')
        polling_interval_attrs.set_mapped_class_variable('polling_interval')
        self.config_model_attributes['polling_interval'] = polling_interval_attrs

        # Retry Limit
        retry_limit_attrs = AMSConfigModelAttribute()
        retry_limit_attrs.set_required(True)
        retry_limit_attrs.set_default(5)
        retry_limit_attrs.set_label('Retry Limit')
        retry_limit_attrs.set_type('int')
        retry_limit_attrs.set_mapped_class_variable('retry_limit')
        self.config_model_attributes['retry_limit'] = retry_limit_attrs

        # Retry Wait
        retry_wait_attrs = AMSConfigModelAttribute()
        retry_wait_attrs.set_required(True)
        retry_wait_attrs.set_default(60)
        retry_wait_attrs.set_label('Retry Wait')
        retry_wait_attrs.set_type('int')
        retry_wait_attrs.set_mapped_class_variable('retry_wait')
        self.config_model_attributes['retry_wait'] = retry_wait_attrs

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
        # @todo: figure out how to handle just returning a single object
        ams_jibbix_options_attrs = AMSConfigModelAttribute()
        ams_jibbix_options_attrs.set_required(False)
        ams_jibbix_options_attrs.set_default(1)
        ams_jibbix_options_attrs.set_max_allowed_entries(1)
        ams_jibbix_options_attrs.set_options([
            1,
            0
        ])
        ams_jibbix_options_attrs.set_label('Set Jibbix Options For This File Route?')
        ams_jibbix_options_attrs.set_type('int')
        ams_jibbix_options_attrs.set_linked_type('Toolkit.Config.AMSJibbixOptions')
        ams_jibbix_options_attrs.set_linked_object('Toolkit.Config.AMSJibbixOptions')
        ams_jibbix_options_attrs.set_linked_label('Setup Jibbix Options')
        ams_jibbix_options_attrs.set_mapped_class_variable('AMSJibbixOptions')
        ams_jibbix_options_attrs.set_return_map_to_variable('AMSJibbixOptions')
        self.config_model_attributes['AMSJibbixOptions'] = ams_jibbix_options_attrs

        # File route Methods
        num_ams_file_route_methods_attrs = AMSConfigModelAttribute()
        num_ams_file_route_methods_attrs.set_required(True)
        num_ams_file_route_methods_attrs.set_default(1)
        num_ams_file_route_methods_attrs.set_max_allowed_entries(1)
        num_ams_file_route_methods_attrs.set_options([
            1
        ])
        num_ams_file_route_methods_attrs.set_label('Setup File Route Method?')
        num_ams_file_route_methods_attrs.set_type('int')
        num_ams_file_route_methods_attrs.set_linked_type('Toolkit.Config.AMSFileRouteMethod')
        num_ams_file_route_methods_attrs.set_linked_object('Toolkit.Config.AMSFileRouteMethod')
        num_ams_file_route_methods_attrs.set_linked_label('Setup File Route Source')
        num_ams_file_route_methods_attrs.set_mapped_class_variable('AMSFileRouteMethod')
        num_ams_file_route_methods_attrs.set_return_map_to_variable('AMSFileRouteMethod')
        self.config_model_attributes['AMSFileRouteMethod'] = num_ams_file_route_methods_attrs

        AMSCommentable._set_config_model_attributes(self)

    def load(self, file_route_name, config_dict):
        """
        :param file_route_name: file route name from the config dict.
        :type file_route_name: str
        :param config_dict: AMS config dictionary (JSON)
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: boolRooste
        """

        try:
            self.raw_config = config_dict
            self.file_route_name = file_route_name
            self._read_int('polling_interval')
            self._read_int('retry_limit')
            self._read_int('retry_wait')
            self._read_string('dependency_check_policy')
            if not self.dependency_check_policy:
                self.dependency_check_policy = self.AMSDefaults.available_dependency_check_policies[0]
            self._read_jibbix_options(self.file_route_name, self.AMSJibbixOptions)
            self._read_file_route_method()
            self._read_dependency_checks()
            AMSCommentable.load(self)

        except AMSMethodException:
            raise
        except Exception as e:
            raise AMSMethodException(e)

    def _read_file_route_method(self):
        """
        This method will set the source_method attribute for the  by loading the AMSFileRouteMethod object.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.AMSFileRouteMethod = AMSFileRouteMethod()
        if 'method' in self.raw_config and self.raw_config['method']:
            self.AMSFileRouteMethod.load(self.file_route_name, self.raw_config['method'])
        else:
            self.AMSLogger.critical('method is not defined for the following file route: ' + self.file_route_name + '.')

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
                ams_dependency_checker.load(dependency_check_name, dependency_check, self.file_route_name)
                self.AMSDependencyChecks[dependency_check_name] = ams_dependency_checker
        else:
            self.AMSLogger.debug('dependency_checks is not defined for the following file route: ' + self.file_route_name + '.')

        return True

    def get_route_zabbix_key(self):
        return "fileroute" + '::' + self.file_route_name

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass