import os, sys
import collections

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSLogFileException
from Toolkit.Config import AMSWebScenarioStep, AbstractAMSConfig, AMSConfigModelAttribute, AMSJibbixOptions

class AMSWebScenario(AbstractAMSConfig):
    """
       This class defines the markets / environments
       """

    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.web_scenario_name = None  # type: str
        self.AMSJibbixOptions = AMSJibbixOptions()
        self.num_web_scenario_steps = None  # type: int
        self.AMSWebScenarioSteps = collections.OrderedDict()  # type: dict[str, AMSWebScenarioStep]

    def get_config_dict_key(self):
        return self.web_scenario_name

    def get_static_config_dict_key(self):
        return 'web_scenarios'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Web Scenario Name
        web_scenario_name_attrs = AMSConfigModelAttribute()
        web_scenario_name_attrs.set_required(True)
        web_scenario_name_attrs.set_default(None)
        web_scenario_name_attrs.set_label('Web Scenario Name')
        web_scenario_name_attrs.set_type('str')
        web_scenario_name_attrs.set_is_config_dict_key(True)
        web_scenario_name_attrs.set_mapped_class_variable('web_scenario_name')
        self.config_model_attributes['web_scenario_name'] = web_scenario_name_attrs

        # AMSJibbixOptions
        ams_jibbix_options_attrs = AMSConfigModelAttribute()
        ams_jibbix_options_attrs.set_required(False)
        ams_jibbix_options_attrs.set_default(1)
        ams_jibbix_options_attrs.set_max_allowed_entries(1)
        ams_jibbix_options_attrs.set_options([
            1,
            0
        ])
        ams_jibbix_options_attrs.set_label('Set Jibbix Options For This Web Scenario?')
        ams_jibbix_options_attrs.set_type('int')
        ams_jibbix_options_attrs.set_linked_type('Toolkit.Config.AMSJibbixOptions')
        ams_jibbix_options_attrs.set_linked_object('Toolkit.Config.AMSJibbixOptions')
        ams_jibbix_options_attrs.set_linked_label('Setup Jibbix Options')
        ams_jibbix_options_attrs.set_mapped_class_variable('AMSJibbixOptions')
        ams_jibbix_options_attrs.set_return_map_to_variable('AMSJibbixOptions')
        self.config_model_attributes['AMSJibbixOptions'] = ams_jibbix_options_attrs

        # Num Web Scenario Steps
        num_web_scenarion_steps_attrs = AMSConfigModelAttribute()
        num_web_scenarion_steps_attrs.set_required(True)
        num_web_scenarion_steps_attrs.set_default(1)
        num_web_scenarion_steps_attrs.set_label('How many Web Scenario Steps would you like to setup?')
        num_web_scenarion_steps_attrs.set_type('int')
        num_web_scenarion_steps_attrs.set_num_required_entries(0)
        num_web_scenarion_steps_attrs.set_linked_object('Toolkit.Config.AMSWebScenarioStep')
        num_web_scenarion_steps_attrs.set_linked_type('dict')
        num_web_scenarion_steps_attrs.set_linked_label('Web Scenario Steps Setup')
        num_web_scenarion_steps_attrs.set_return_map_to_variable('AMSWebScenarioSteps')
        num_web_scenarion_steps_attrs.set_mapped_class_variable('num_web_scenario_steps')
        self.config_model_attributes['num_web_scenario_steps'] = num_web_scenarion_steps_attrs

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
            self._read_jibbix_options(self.web_scenario_name, self.AMSJibbixOptions)
            self._read_web_scenario_step()
        except AMSLogFileException:
            raise
        except Exception as e:
            raise AMSLogFileException(e)

    def _read_web_scenario_step(self):
        """
        This method will set the projects dictionary of AMSWebScenario objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.num_web_scenario_steps = 0
        if 'web_scenario_step' in self.raw_config and self.raw_config['web_scenario_step'] and isinstance(self.raw_config['web_scenario_step'], dict):
            for name, data in self.raw_config['web_scenario_step'].iteritems():
                self.num_web_scenario_steps += 1
                web_scenario = AMSWebScenarioStep()
                web_scenario.load(name, data)
                self.AMSWebScenarioSteps[name] = web_scenario

        else:
            self.AMSLogger.debug('No web scenario steps set in config.')
            return False

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