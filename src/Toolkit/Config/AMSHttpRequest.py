import os
import sys
import collections

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSLogFileException
from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute, AMSDictEntry

class AMSHttpRequest(AbstractAMSConfig):
    """
       This class defines the markets / environments
       """

    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.web_scenario_name = None  # type: str
        self.url = None  # type: str
        self.method = None  # type: str
        self.verify_ssl = None  # type: bool
        self.num_params = None  # type: int
        self.params = collections.OrderedDict()  # type: dict[str, AMSDictEntry]
        self.num_headers = None  # type: int
        self.headers = collections.OrderedDict()  # type: dict[str, AMSDictEntry]
        self.timeout = None  # type: int
        self.http_proxy = None  # type: str
        self.https_proxy = None  # type: str

    def get_config_dict_key(self):
        return self.web_scenario_name

    def get_static_config_dict_key(self):
        return 'http_request'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # URL
        url_attrs = AMSConfigModelAttribute()
        url_attrs.set_required(True)
        url_attrs.set_default(None)
        url_attrs.set_label('URL')
        url_attrs.set_type('str')
        url_attrs.set_mapped_class_variable('url')
        self.config_model_attributes['url'] = url_attrs

        # Method
        method_attrs = AMSConfigModelAttribute()
        method_attrs.set_required(False)
        method_attrs.set_default('GET')
        method_attrs.set_label('HTTP Method')
        method_attrs.set_type('str')
        method_attrs.set_options([
            'GET',
            'PUT',
            'POST',
            'CONNECT',
            'OPTIONS',
            'HEAD',
            'DELETE',
            'TRACE'
        ])
        method_attrs.set_mapped_class_variable('method')
        self.config_model_attributes['method'] = method_attrs

        # Verify
        verify_attrs = AMSConfigModelAttribute()
        verify_attrs.set_required(False)
        verify_attrs.set_default(True)
        verify_attrs.set_label('Verify SSL Cert (if SSL connection)')
        verify_attrs.set_type('bool')
        verify_attrs.set_mapped_class_variable('verify_ssl')
        self.config_model_attributes['verify_ssl'] = verify_attrs

        # Params
        params_attrs = AMSConfigModelAttribute()
        params_attrs.set_required(False)
        params_attrs.set_default(0)
        params_attrs.set_label('List of HTTP Parameters')
        params_attrs.set_type('int')
        params_attrs.set_num_required_entries(0)
        params_attrs.set_linked_object('Toolkit.Config.AMSDictEntry')
        params_attrs.set_linked_type('dict')
        params_attrs.set_linked_label('HTTP Parameters Setup')
        params_attrs.set_return_map_to_variable('params')
        params_attrs.set_mapped_class_variable('num_params')
        self.config_model_attributes['num_params'] = params_attrs

        # Headers
        headers_attrs = AMSConfigModelAttribute()
        headers_attrs.set_required(False)
        headers_attrs.set_default(0)
        headers_attrs.set_label('List of HTTP Headers')
        headers_attrs.set_type('int')
        headers_attrs.set_num_required_entries(0)
        headers_attrs.set_linked_object('Toolkit.Config.AMSDictEntry')
        headers_attrs.set_linked_type('dict')
        headers_attrs.set_linked_label('HTTP Headers Setup')
        headers_attrs.set_return_map_to_variable('headers')
        headers_attrs.set_mapped_class_variable('num_headers')
        self.config_model_attributes['num_headers'] = headers_attrs

        # Timeout
        timeout_attrs = AMSConfigModelAttribute()
        timeout_attrs.set_required(False)
        timeout_attrs.set_default(30)
        timeout_attrs.set_label('Time to wait (in seconds)')
        timeout_attrs.set_type('int')
        timeout_attrs.set_mapped_class_variable('timeout')
        self.config_model_attributes['timeout'] = timeout_attrs

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

    def load(self, web_scenario_name, config_dict):
        """
        :param web_scenario_name: full path of log file / pattern from the config dict.
        :type web_scenario_name: str
        :param config_dict: List of strings to search for
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.web_scenario_name = web_scenario_name
            self._read_string('url')
            self._read_string('method')
            self._read_bool('verify_ssl')
            self._read_dict('params', 'num_params')
            self._read_dict('headers', 'num_headers')
            self._read_int('timeout')
            self._read_string('http_proxy')
            self._read_string('https_proxy')
        except AMSLogFileException:
            raise
        except Exception as e:
            raise AMSLogFileException(e)

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass