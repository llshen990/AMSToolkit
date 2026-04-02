import os, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSLogFileException
from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute

class AMSHttpResponse(AbstractAMSConfig):
    """
       This class defines the markets / environments
       """

    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.web_scenario_name = None  # type: str
        self.status_code = None  # type: int
        self.regex = None # type: str
        self.header = None # type: str

    def get_config_dict_key(self):
        return self.web_scenario_name

    def get_static_config_dict_key(self):
        return 'http_response'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Status Code
        status_code_attrs = AMSConfigModelAttribute()
        status_code_attrs.set_required(False)
        status_code_attrs.set_default(200)
        status_code_attrs.set_label('HTTP Status Code')
        status_code_attrs.set_type('int')
        status_code_attrs.set_mapped_class_variable('status_code')
        self.config_model_attributes['status_code'] = status_code_attrs

        # Regex
        regex_attrs = AMSConfigModelAttribute()
        regex_attrs.set_required(False)
        regex_attrs.set_default(None)
        regex_attrs.set_label('Regex to match against HTTP Response text')
        regex_attrs.set_type('str')
        regex_attrs.set_mapped_class_variable('regex')
        self.config_model_attributes['regex'] = regex_attrs

        # Header
        header_attrs = AMSConfigModelAttribute()
        header_attrs.set_required(False)
        header_attrs.set_default(None)
        header_attrs.set_label('Header to require in HTTP Response headers')
        header_attrs.set_type('str')
        header_attrs.set_mapped_class_variable('header')
        self.config_model_attributes['header'] = header_attrs

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
            self._read_int('status_code')
            self._read_string('regex')
            self._read_string('regex')
            self._read_string('header')
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