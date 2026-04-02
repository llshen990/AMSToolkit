import os, sys, collections

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSSchedule, AbstractAMSConfig, AMSConfigModelAttribute
from Toolkit.Exceptions import AMSProjectException

class AMSProject(AbstractAMSConfig):
    default_signal_dir = os.sep + 'signal'
    """
       This class defines the markets / environments
       """

    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.raw_config = collections.OrderedDict()
        self.project_name = None  # type: str
        self.home_dir = None  # type: str
        self.signal_dir = None  # type: str
        self.num_ams_schedules = None  # type: int
        self.AMSSchedules = collections.OrderedDict()  # type: dict[str, AMSSchedule]

    def get_config_dict_key(self):
        return self.project_name

    def get_static_config_dict_key(self):
        return 'projects'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Project Name
        project_name_attrs = AMSConfigModelAttribute()
        project_name_attrs.set_required(True)
        project_name_attrs.set_default(None)
        project_name_attrs.set_label('Project Name (TEST, PROD, DEV, etc)')
        project_name_attrs.set_type('str')
        project_name_attrs.set_is_config_dict_key(True)
        project_name_attrs.set_mapped_class_variable('project_name')
        self.config_model_attributes['project_name'] = project_name_attrs

        # Project Home Dir
        home_dir_attrs = AMSConfigModelAttribute()
        home_dir_attrs.set_required(True)
        home_dir_attrs.set_default(None)
        home_dir_attrs.set_label('Project Home Directory')
        home_dir_attrs.set_type('str')
        home_dir_attrs.set_mapped_class_variable('home_dir')
        home_dir_attrs.set_share_value(True)
        home_dir_attrs.set_return_transform('abspath')
        self.config_model_attributes['home_dir'] = home_dir_attrs

        # Signal Dir
        signal_dir_attrs = AMSConfigModelAttribute()
        signal_dir_attrs.set_required(True)
        signal_dir_attrs.set_default(self.default_signal_dir)
        signal_dir_attrs.set_label('Signal Directory')
        signal_dir_attrs.set_type('str')
        signal_dir_attrs.set_mapped_class_variable('signal_dir')
        signal_dir_attrs.set_share_value(True)
        signal_dir_attrs.set_return_transform('abspath')
        self.config_model_attributes['signal_dir'] = signal_dir_attrs

        num_ams_schedules_attrs = AMSConfigModelAttribute()
        num_ams_schedules_attrs.set_required(False)
        num_ams_schedules_attrs.set_default(1)
        num_ams_schedules_attrs.set_label('How many schedules would you like to setup?')
        num_ams_schedules_attrs.set_type('int')
        num_ams_schedules_attrs.set_num_required_entries(0)
        num_ams_schedules_attrs.set_linked_object('Toolkit.Config.AMSSchedule')
        num_ams_schedules_attrs.set_linked_type('dict')
        num_ams_schedules_attrs.set_linked_label('Schedule Setup')
        num_ams_schedules_attrs.set_return_map_to_variable('AMSSchedules')
        num_ams_schedules_attrs.set_mapped_class_variable('num_ams_schedules')
        self.config_model_attributes['num_ams_schedules'] = num_ams_schedules_attrs

    def load(self, project_name, config_dict):
        """
        :param project_name: project name from the config dict.
        :type project_name: str
        :param config_dict: AMS config dictionary (JSON)
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.project_name = project_name
            self._read_home_dir()
            self._read_signal_dir()
            self._read_schedules()
        except AMSProjectException:
            raise
        except Exception as e:
            raise AMSProjectException(e)

    def _read_home_dir(self):
        """
        This method will set the home_dir variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'home_dir' in self.raw_config and self.raw_config['home_dir']:
            self.home_dir = str(self.raw_config['home_dir']).strip()
        else:
            self.AMSLogger.critical('home_dir is not defined in the config for this project: ' + self.project_name)
            return False

        return True

    def _read_signal_dir(self):
        """
        This method will set the signal_dir variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'signal_dir' in self.raw_config and self.raw_config['signal_dir']:
            self.signal_dir = str(self.raw_config['signal_dir']).strip()
        else:
            self.AMSLogger.critical('signal_dir is not defined in the config for this project: ' + self.project_name)
            return False

        return True

    def _read_schedules(self):
        """
        This method will set the schedules dictionary of AMSSchedule objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        self.num_ams_schedules = 0
        if 'schedules' in self.raw_config and self.raw_config['schedules'] and isinstance(self.raw_config['schedules'], dict):
            for schedule_name, schedule_data in self.raw_config['schedules'].iteritems():
                self.num_ams_schedules += 1
                ams_schedule = AMSSchedule()
                ams_schedule.load(self.project_name, schedule_name, schedule_data)
                self.AMSSchedules[schedule_name] = ams_schedule

        else:
            self.AMSLogger.critical('No schedules set in config.')
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

    def _validate_home_dir(self, tmp_input):
        return self._ams_validate_directory(tmp_input)

    def _validate_signal_dir(self, tmp_input):
        return self._ams_validate_directory(tmp_input)
