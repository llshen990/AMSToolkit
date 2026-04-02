import os, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSLogFileException
from Toolkit.Config import AMSHttpRequest, AMSHttpResponse, AbstractAMSConfig, AMSConfigModelAttribute

class AMSWebScenarioStep(AbstractAMSConfig):
    """
       This class defines the markets / environments
       """

    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.step_name = None  # type: str
        self.AMSHttpRequest = AMSHttpRequest()  # type: AMSHttpRequest
        self.AMSHttpResponse = AMSHttpResponse()  # type: AMSHttpResponse

    def get_config_dict_key(self):
        return self.step_name

    def get_static_config_dict_key(self):
        return 'web_scenario_step'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Web Scenario Step Name
        web_scenario_step_name_attrs = AMSConfigModelAttribute()
        web_scenario_step_name_attrs.set_required(True)
        web_scenario_step_name_attrs.set_default(None)
        web_scenario_step_name_attrs.set_label('Web Scenario Step Name')
        web_scenario_step_name_attrs.set_type('str')
        web_scenario_step_name_attrs.set_is_config_dict_key(True)
        web_scenario_step_name_attrs.set_mapped_class_variable('step_name')
        self.config_model_attributes['step_name'] = web_scenario_step_name_attrs

        # HTTP Request
        request_attrs = AMSConfigModelAttribute()
        request_attrs.set_required(True)
        request_attrs.set_default(1)
        request_attrs.set_max_allowed_entries(1)
        request_attrs.set_options([
            1,
            0
        ])
        request_attrs.set_label('HTTP Request')
        request_attrs.set_type('int')
        request_attrs.set_linked_type('Toolkit.Config.AMSHttpRequest')
        request_attrs.set_linked_object('Toolkit.Config.AMSHttpRequest')
        request_attrs.set_linked_label('Setup HTTP Request')
        request_attrs.set_mapped_class_variable('AMSHttpRequest')
        request_attrs.set_return_map_to_variable('AMSHttpRequest')
        self.config_model_attributes['AMSHttpRequest'] = request_attrs

        # HTTP Response
        response_attrs = AMSConfigModelAttribute()
        response_attrs.set_required(True)
        response_attrs.set_default(1)
        response_attrs.set_max_allowed_entries(1)
        response_attrs.set_options([
            1
        ])
        response_attrs.set_label('HTTP Response')
        response_attrs.set_type('int')
        response_attrs.set_linked_type('Toolkit.Config.AMSHttpResponse')
        response_attrs.set_linked_object('Toolkit.Config.AMSHttpResponse')
        response_attrs.set_linked_label('Setup HTTP Response')
        response_attrs.set_mapped_class_variable('AMSHttpResponse')
        response_attrs.set_return_map_to_variable('AMSHttpResponse')
        self.config_model_attributes['AMSHttpResponse'] = response_attrs

    def load(self, step_name, config_dict):
        """
        :param step_name: full path of log file / pattern from the config dict.
        :type step_name: str
        :param config_dict: List of strings to search for
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.step_name = step_name
            self._read_http_request()
            self._read_http_response()
        except AMSLogFileException:
            raise
        except Exception as e:
            raise AMSLogFileException(e)

    def _read_http_request(self):
        """
        This method will read the HttpRequest of the web scenario.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.AMSHttpRequest = AMSHttpRequest()
        if 'http_request' in self.raw_config and self.raw_config['http_request']:
            self.AMSHttpRequest.load(self.step_name, self.raw_config['http_request'])
        else:
            self.AMSLogger.critical('http_request is not defined for the following web scenario step: ' + self.step_name + '.')

        return True

    def _read_http_response(self):
        """
        This method will read the HttpResponse of the web scenario.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.AMSHttpResponse = AMSHttpResponse()
        if 'http_response' in self.raw_config and self.raw_config['http_response']:
            self.AMSHttpResponse.load(self.step_name, self.raw_config['http_response'])
        else:
            self.AMSLogger.critical('http_response is not defined for the following web scenario step: ' + self.step_name + '.')

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