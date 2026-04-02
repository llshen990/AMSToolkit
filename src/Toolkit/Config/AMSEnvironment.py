import os
import re
from pydoc import locate
import sys
import collections

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute
from Toolkit.Exceptions import AMSEnvironmentException
from json import loads as json_loads

class AMSEnvironment(AbstractAMSConfig):
    """
       This class defines the markets / environments
       """

    def __init__(self, new_config=False):
        self.AMSDefaults = locate('Toolkit.Lib.Defaults.AMSDefaults')()
        AbstractAMSConfig.__init__(self)

        self.tla = None  # type: str
        self.confluence_space = None  # type: str
        self.run_user = None  # type: str
        self.env_type = None  # type: str
        self.env_function = None  # type: str
        self.hostname = None  # type: str
        self.new_config = True if new_config else False
        self.service = collections.OrderedDict()

        # set the config model attributes
        self._set_config_model_attributes()

    def get_config_dict_key(self):
        return self.hostname

    def get_static_config_dict_key(self):
        return 'environments'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """
        # My Hostname
        my_hostname_attrs = AMSConfigModelAttribute()
        my_hostname_attrs.set_required(True)
        my_hostname_attrs.set_default(self.AMSDefaults.my_hostname)
        my_hostname_attrs.set_label('My Hostname')
        my_hostname_attrs.set_type('str')
        my_hostname_attrs.set_is_config_dict_key(True)
        my_hostname_attrs.set_allow_edit(False)
        my_hostname_attrs.set_mapped_class_variable('hostname')
        my_hostname_attrs.set_include_in_config_file(False)
        self.config_model_attributes['hostname'] = my_hostname_attrs

        # Environment Type
        env_type_attrs = AMSConfigModelAttribute()
        env_type_attrs.set_required(True)
        env_type_attrs.set_default('DEV')
        env_type_attrs.set_label('Environment Type (DEV, TEST, QA, PROD etc)')
        env_type_attrs.set_type('str')
        env_type_attrs.set_mapped_class_variable('env_type')
        self.config_model_attributes['env_type'] = env_type_attrs

        # Environment Function
        environment_function_attrs = AMSConfigModelAttribute()
        environment_function_attrs.set_required(True)
        environment_function_attrs.set_default('compute')
        environment_function_attrs.set_label('Environment Function')
        environment_function_attrs.set_type('str')
        environment_function_attrs.set_mapped_class_variable('env_function')
        environment_function_attrs.set_options([
            'all-in-one',
            'compute',
            'metadata',
            'midtier',
            'secondary_midtier',
            'cas_controller',
            'cas_worker',
            'terminal',
            'grid_metadata',
            'grid_compute',
            'grid_midtier',
            'sasgsub',
            'grid_terminal'
            'grid_node',
            'oa_compute'
            'va',
            'va_compute',
            'va_head_node',
            'va_worker_node',
            'cloudera_name_node',
            'cloudera_edge_node',
            'cloudera_data_node'
        ])
        self.config_model_attributes['env_function'] = environment_function_attrs

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
        tla_attrs.set_share_value(True)
        self.config_model_attributes['tla'] = tla_attrs

        # Confluence Space
        confluence_space_attrs = AMSConfigModelAttribute()
        confluence_space_attrs.set_required(True)
        if self.AMSDefaults.default_tla:
            confluence_space_attrs.set_default(self.AMSDefaults.default_tla + "INT")
        else:
            confluence_space_attrs.set_default(self.AMSDefaults.default_confluence_space)
        confluence_space_attrs.set_label('Confluence Space for this TLA (ie. TLAINT)')
        confluence_space_attrs.set_type('str')
        confluence_space_attrs.set_mapped_class_variable('confluence_space')
        self.config_model_attributes['confluence_space'] = confluence_space_attrs

        # Run User
        run_user_attrs = AMSConfigModelAttribute()
        run_user_attrs.set_required(False)
        if self.AMSDefaults.default_tla:
            run_user_attrs.set_default(self.AMSDefaults.default_tla.lower() + "run")
        else:
            run_user_attrs.set_default(None)
        run_user_attrs.set_label('Run User')
        run_user_attrs.set_type('str')
        run_user_attrs.set_mapped_class_variable('run_user')
        self.config_model_attributes['run_user'] = run_user_attrs

        service_attrs = AMSConfigModelAttribute()
        service_attrs.set_required(False)
        service_attrs.set_label('Service Configuration')
        service_attrs.set_type('dict')
        service_attrs.set_allow_edit(False)
        service_attrs.set_hide_from_user_display(True)
        service_attrs.set_mapped_class_variable('service')
        self.config_model_attributes['service'] = service_attrs

        return True

    def load(self, hostname, config_dict):
        """
        :param hostname: hostname from the config dict.
        :type hostname: str
        :param config_dict: AMS config dictionary (JSON)
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.hostname = hostname.strip()
            self._read_tla()
            self._read_run_user()
            self._read_env_function()
            self._read_env_type()
            self._read_json('service')
            self._read_string('confluence_space')
        except AMSEnvironmentException:
            raise
        except Exception as e:
            raise AMSEnvironmentException(e)

    def _read_tla(self):
        """
        This method will set the tla variable for the environment.  If not defined, it will set it based off of hostname.
        :return: True upon success or exception upon failure.
        :rtype: bool
        """
        if 'tla' in self.raw_config and self.raw_config['tla']:
            self.tla = str(self.raw_config['tla']).strip()
        else:
            try:
                self._set_tla_from_hostname()
            except AMSEnvironmentException as e:
                self.AMSLogger.critical('No tla set in config or environment: ' + str(e))
                return False

        return True

    def _set_tla_from_hostname(self):
        """
        This method will try to set the TLA based off of the hostname.
        :return: True upon success, exception upon failure.
        :rtype: bool
        """
        try:
            self.tla = re.search('^([a-z]+)\d+', self.hostname).group(1).strip()
            self.AMSLogger.info('tla is not set in config.  Going to set to ' + self.tla + ' based off of hostname')
        except Exception as e:
            raise AMSEnvironmentException(e)

    def _read_run_user(self):
        """
        This method will set the run_user variable for the environment.  If not defined, it will set it based off of hostname.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'run_user' in self.raw_config and self.raw_config['run_user']:
            self.run_user = str(self.raw_config['run_user']).strip()
        elif self.tla:
            try:
                self.AMSLogger.info('run_user is not set in config.  Trying to set to run_user based off of TLA')
                self._set_run_user_from_tla()
            except AMSEnvironmentException as e:
                self.AMSLogger.critical('run_user could not be set from the TLA: ' + str(e))
                return False
        else:
            if self.new_config:
                self.AMSLogger.info('run_user is not set in config and could not be set from the TLA.')
            else:
                self.AMSLogger.critical('run_user is not set in config and could not be set from the TLA.')
            return False

        return True

    def read_run_user(self):
        """
        This is the public access for self._read_run_user()
        :return: True upon success or False upon failure.
        :rtype: bool
        """

        return self._read_run_user()

    def _set_run_user_from_tla(self):
        """
        This method sets the run user from the TLA.
        :return: True upon success or exception on failure.
        :rtype: bool
        """
        if self.tla:
            self.run_user = str(self.tla).lower() + 'run'
        else:
            raise AMSEnvironmentException('Could not set run_user from TLA as the tla attribute is not set')
        return True

    def _read_env_type(self):
        """
        This method will set the env_type variable for the environment.
        :return: True upon success or exception upon failure.
        :rtype: bool
        """
        if 'env_type' in self.raw_config and self.raw_config['env_type']:
            self.env_type = str(self.raw_config['env_type']).strip()
        else:
            self.AMSLogger.info('env_type is not set in config.')

        return True

    def _read_env_function(self):
        """
        This method will set the env_function variable for the environment.
        :return: True upon success or exception upon failure.
        :rtype: bool
        """
        if 'env_function' in self.raw_config and self.raw_config['env_function']:
            self.env_function = str(self.raw_config['env_function']).strip()
        else:
            self.AMSLogger.info('env_function is not set in config.')

        return True

    def create_server_dict(self, conf_file):
        """
        creates dict of servers from given config json file
        :param conf_file: json file containing environment information
        :return: server_dict: dict consisting of hostname: (env_type, env_function)
        """
        with open(conf_file) as conf_json:
            server_list = {}
            # we only care about the environment portion
            conf_dict = json_loads(conf_json.read())['environments']
            # the key list here is a list of all hostnames
            for key in conf_dict.keys():
                server_list[key] = (conf_dict[key]['env_type'], conf_dict[key]['env_function'])
            # trim out terminal server(s)
            return {k: v for k, v in server_list.items() if v[1] != 'terminal'}

    def get_midtier_hostname(self, server_dict):
        """
        get midtier hostname from server dict
        :param server_dict:
        :return str: hostname
        """
        for k in server_dict.keys():
            if server_dict[k][1].upper() == 'MIDTIER':
                # convert from unicode
                return str(k)
            # in a well-formed server dict there will never be a midtier and an all-in-one
            elif server_dict[k][1].upper() == 'ALL-IN-ONE':
                return str(k)

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass
