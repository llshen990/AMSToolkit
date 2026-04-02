import sys

import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AbstractAMSConfig, AMSCommentable, AMSConfigModelAttribute
from Toolkit.Exceptions import AMSLogFileException, AMSValidationException
from lib.Validators import FileExistsValidator


class AMSDependencyChecker(AMSCommentable):
    """
       This class defines the markets / environments
       """

    def __init__(self):
        # Dynamically import the Defaults module
        # The dependency on AMSDefaults in the Defaults package causes import issues
        # import importlib
        from pydoc import locate
        self.AMSDefaults = locate('Toolkit.Lib.Defaults.AMSDefaults')()
        AMSCommentable.__init__(self)
        self.dependency_check_name = None  # type: str
        self.schedule_name = None  # type: str
        self.type = None  # type: str
        self.dependency = None  # type: str
        self.descriptor_file = None #type:str
        self.max_attempts = None  # type: int
        self.attempt_interval = None  # type: int

    def check_dependency(self, ams_config):
        """
        This method will fire off a dependency check in a separate thread and monitor the results
        :param ams_config: AMSConfig
        :type ams_config: AMSConfig
        :return: True upon success, false on failure
        :rtype: AMSReturnCode
        """
        self.AMSLogger.debug('In check_dependency for %s' % self.dependency_check_name)
        from pydoc import locate
        dependency_check = locate('Toolkit.Lib.DependencyChecks.'+'AMS' + self.type + 'DependencyCheck')(ams_config, self)
        # set the result message to the commandline output
        result = dependency_check.evaluate_dependency()
        if not result.job_success:
            result.message = dependency_check.commandline_output()
        return result

    def get_config_dict_key(self):
        return self.dependency_check_name

    def get_static_config_dict_key(self):
        return 'dependency_checks'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Dependency Check Name
        dependency_check_name_attrs = AMSConfigModelAttribute()
        dependency_check_name_attrs.set_required(True)
        dependency_check_name_attrs.set_default(None)
        dependency_check_name_attrs.set_label('Dependency Check Name')
        dependency_check_name_attrs.set_type('str')
        dependency_check_name_attrs.set_is_config_dict_key(True)
        dependency_check_name_attrs.set_mapped_class_variable('dependency_check_name')
        self.config_model_attributes['dependency_check_name'] = dependency_check_name_attrs

        # Dependency Type
        type_attrs = AMSConfigModelAttribute()
        type_attrs.set_required(True)
        type_attrs.set_default(None)
        type_attrs.set_options(self.AMSDefaults.dependency_checker_allowed_types)
        type_attrs.set_label('Type of Dependency Check?')
        type_attrs.set_type('str')
        type_attrs.set_mapped_class_variable('type')
        self.config_model_attributes['type'] = type_attrs

        # Dependency
        dependency_attrs = AMSConfigModelAttribute()
        dependency_attrs.set_required(True)
        dependency_attrs.set_default(None)
        dependency_attrs.set_label('Dependency')
        dependency_attrs.set_type('str')
        dependency_attrs.set_mapped_class_variable('dependency')
        self.config_model_attributes['dependency'] = dependency_attrs

        # Descriptor_file
        descriptor_file_attrs = AMSConfigModelAttribute()
        descriptor_file_attrs.set_required(False)
        descriptor_file_attrs.set_default(None)
        descriptor_file_attrs.set_label('Descriptor File')
        descriptor_file_attrs.set_type('str')
        descriptor_file_attrs.set_dependent_variable('type')
        descriptor_file_attrs.set_dependent_value('DQ')
        descriptor_file_attrs.set_mapped_class_variable('descriptor_file')
        self.config_model_attributes['descriptor_file'] = descriptor_file_attrs

        # Dependency Max Attempts
        max_attempts_attrs = AMSConfigModelAttribute()
        max_attempts_attrs.set_required(True)
        max_attempts_attrs.set_default(self.AMSDefaults.dependency_checker_default_max_attempts)
        max_attempts_attrs.set_label('Max attempts to try dependency check?')
        max_attempts_attrs.set_type('int')
        max_attempts_attrs.set_mapped_class_variable('max_attempts')
        self.config_model_attributes['max_attempts'] = max_attempts_attrs

        # Dependency Max Attempts
        attempt_interval_attrs = AMSConfigModelAttribute()
        attempt_interval_attrs.set_required(False)
        attempt_interval_attrs.set_default(self.AMSDefaults.dependency_checker_default_attempt_interval)
        attempt_interval_attrs.set_label('Number of seconds to wait before attempting dependency check again?')
        attempt_interval_attrs.set_type('int')
        attempt_interval_attrs.set_mapped_class_variable('attempt_interval')
        self.config_model_attributes['attempt_interval'] = attempt_interval_attrs

        AMSCommentable._set_config_model_attributes(self)

    def load(self, dependency_check_name, config_dict, schedule_name=None):
        """
        :param dependency_check_name: full path of log file / pattern from the config dict.
        :type dependency_check_name: str
        :param config_dict: List of strings to search for
        :type config_dict: dict
        :param schedule_name : schedule
        :type schedule_name : str
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.dependency_check_name = dependency_check_name
            self.schedule_name = schedule_name
            self._read_type()
            self._read_dependency()
            self._read_max_attempts()
            self._read_attempt_interval()
            AMSCommentable.load(self)

        except AMSLogFileException:
            raise
        except Exception as e:
            raise AMSLogFileException(e)

    def _read_type(self):
        """
        This method will set the type variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'type' in self.raw_config and self.raw_config['type']:
            self.type = str(self.raw_config['type']).strip()
        else:
            self.AMSLogger.critical('type is not defined for the following dependency check: ' + self.dependency_check_name + '.')

        return True

    def _read_dependency(self):
        """
        This method will set the dependency variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'dependency' in self.raw_config and self.raw_config['dependency']:
            self.dependency = str(self.raw_config['dependency']).strip()
        else:
            self.AMSLogger.critical('dependency is not defined for the following dependency check: ' + self.dependency_check_name + '.')

        return True

    def _read_max_attempts(self):
        """
        This method will set the max_attempts variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'max_attempts' in self.raw_config and self.raw_config['max_attempts']:
            self.max_attempts = int(self.raw_config['max_attempts'])
        else:
            self.AMSLogger.critical('max_attempts is not defined for the following dependency check: ' + self.dependency_check_name + '.')

        return True

    def _read_attempt_interval(self):
        """
        This method will set the attempt_interval variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'attempt_interval' in self.raw_config and self.raw_config['attempt_interval']:
            self.attempt_interval = int(self.raw_config['attempt_interval'])
        else:
            self.AMSLogger.critical('attempt_interval is not defined for the following dependency check: ' + self.dependency_check_name + '.')

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

    def _validate_dependency(self, tmp_input):
        if self.type == 'Script':
            script_nm = tmp_input.split()[0]
            fev = FileExistsValidator(self.debug)
            if not fev.validate(script_nm):
                raise AMSValidationException(fev.format_errors())
            elif not fev.is_exe(script_nm):
                fev.add_error(script_nm, 'File is not executable')
                raise AMSValidationException(fev.format_errors())
            return True
        elif self.type.startswith('Signal'):
            # Validate the directory of the file, not the file itself
            directory = os.path.dirname(tmp_input)
            if directory is not '':
                self.AMSLogger.debug("Validating directory " + directory)
                return self._ams_validate_directory(directory)
            else:
                self.AMSLogger.debug("Using default signal directory for Signal dependency check")
                return True
        else:
            # For now we don't validate other types
            return True
