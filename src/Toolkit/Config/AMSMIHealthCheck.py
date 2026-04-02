import os, sys, socket

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from urlparse import urlparse
from Toolkit.Exceptions import AMSSecretException
from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute, AMSJibbixOptions, AMSSecret


class AMSMIHealthCheck(AbstractAMSConfig):
    """
       This class defines the markets / environments
       """
    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.raw_config = None
        self.mi_healthcheck_name = None  # type: str
        self.midtier_url = None  # type: str
        self.hostname = None  # type: str
        self.verify_ssl = None  # type: bool
        self.AMSSecret = AMSSecret()
        self.http_proxy = None  # type: str
        self.https_proxy = None  # type: str
        self.timeout = None  # type: int
        self.AMSJibbixOptions = AMSJibbixOptions()

    def get_config_dict_key(self):
        return self.mi_healthcheck_name

    def get_static_config_dict_key(self):
        return 'mi_healthchecks'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Healthcheck Name
        attrs = AMSConfigModelAttribute()
        attrs.set_required(True)
        attrs.set_default(None)
        attrs.set_label('MI Health Check Name')
        attrs.set_type('str')
        attrs.set_is_config_dict_key(True)
        attrs.set_mapped_class_variable('mi_healthcheck_name')
        self.config_model_attributes['mi_healthcheck_name'] = attrs

        # MI Midtier URL
        attrs = AMSConfigModelAttribute()
        attrs.set_required(True)
        attrs.set_default('http://'+self.my_hostname+':8080')
        attrs.set_label('MI Midtier Base URL')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('midtier_url')
        self.config_model_attributes['midtier_url'] = attrs

        # Verify SSL Certs
        attrs = AMSConfigModelAttribute()
        attrs.set_required(False)
        attrs.set_default(True)
        attrs.set_label('Verify SSL Certs')
        attrs.set_type('bool')
        attrs.set_options([
            True,
            False
        ])
        attrs.set_mapped_class_variable('verify_ssl')
        self.config_model_attributes['verify_ssl'] = attrs

        # AMSSecret
        ams_secret_attrs = AMSConfigModelAttribute()
        ams_secret_attrs.set_required(False)
        ams_secret_attrs.set_default(1)
        ams_secret_attrs.set_max_allowed_entries(1)
        ams_secret_attrs.set_options([
            1,
            0
        ])
        ams_secret_attrs.set_label('Secret For This MI Healthcheck?')
        ams_secret_attrs.set_type('int')
        ams_secret_attrs.set_linked_type('Toolkit.Config.AMSSecret')
        ams_secret_attrs.set_linked_object('Toolkit.Config.AMSSecret')
        ams_secret_attrs.set_linked_label('Setup Secret')
        ams_secret_attrs.set_mapped_class_variable('AMSSecret')
        ams_secret_attrs.set_return_map_to_variable('AMSSecret')
        self.config_model_attributes['AMSSecret'] = ams_secret_attrs

        # HTTP Proxy
        attrs = AMSConfigModelAttribute()
        attrs.set_required(False)
        if 'http_proxy' in os.environ:
            attrs.set_default(os.environ['http_proxy'])
        attrs.set_label('HTTP Proxy')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('http_proxy')
        self.config_model_attributes['http_proxy'] = attrs

        # HTTPS Proxy
        attrs = AMSConfigModelAttribute()
        attrs.set_required(False)
        if 'https_proxy' in os.environ:
            attrs.set_default(os.environ['https_proxy'])
        attrs.set_label('HTTPS Proxy')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('https_proxy')
        self.config_model_attributes['https_proxy'] = attrs

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
        ams_jibbix_options_attrs.set_label('Set Jibbix Options For This MI Healthcheck?')
        ams_jibbix_options_attrs.set_type('int')
        ams_jibbix_options_attrs.set_linked_type('Toolkit.Config.AMSJibbixOptions')
        ams_jibbix_options_attrs.set_linked_object('Toolkit.Config.AMSJibbixOptions')
        ams_jibbix_options_attrs.set_linked_label('Setup Jibbix Options')
        ams_jibbix_options_attrs.set_mapped_class_variable('AMSJibbixOptions')
        ams_jibbix_options_attrs.set_return_map_to_variable('AMSJibbixOptions')
        self.config_model_attributes['AMSJibbixOptions'] = ams_jibbix_options_attrs

        # Timeout
        attrs = AMSConfigModelAttribute()
        attrs.set_required(False)
        attrs.set_default(300)
        attrs.set_label('Timeout')
        attrs.set_type('int')
        attrs.set_mapped_class_variable('timeout')
        self.config_model_attributes['timeout'] = attrs

    def load(self, mi_healthcheck_name, config_dict):
        """
        :param mi_healthcheck_name: name of the secret
        :type mi_healthcheck_name: str
        :param config_dict: List of strings to search for
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.mi_healthcheck_name = mi_healthcheck_name
            self._read_string('midtier_url')
            # After reading the midtier_url, set the hostname
            try:
                parsed_url = urlparse(self.midtier_url)
                self.hostname = parsed_url.hostname
            except Exception as e:
                self.AMSLogger.warning('Cannot parse midtier_url for hostname')
            self._read_bool('verify_ssl')
            self._read_secret()
            self._read_string('http_proxy')
            self._read_string('https_proxy')
            self._read_int('timeout')
            self._read_jibbix_options(self.mi_healthcheck_name, self.AMSJibbixOptions)
        except AMSSecretException:
            raise
        except Exception as e:
            raise AMSSecretException(e)

    def _read_secret(self):
        """
        This method will set the secrets attribute for the file route by loading the AMSSecret object.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.AMSSecret = AMSSecret()
        if 'secrets' in self.raw_config and self.raw_config['secrets']:
            self.AMSSecret.load(self.mi_healthcheck_name, self.raw_config['secrets'])
        else:
            self.AMSLogger.critical('secrets is not defined for the following mi healthcheck check: ' + self.mi_healthcheck_name + '.')

        return True

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass