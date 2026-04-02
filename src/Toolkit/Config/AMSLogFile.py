import os, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSLogFileException
from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute
from Toolkit.Lib.Helpers import OutputFormatHelper

class AMSLogFile(AbstractAMSConfig):
    """
       This class defines the markets / environments
       """

    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.orig_log_file_path = None  # type: str
        self.regex_to_search = []

    def get_config_dict_key(self):
        return self.orig_log_file_path

    def get_static_config_dict_key(self):
        return 'log_file_locations'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Orig Log File Path
        orig_log_file_path_attrs = AMSConfigModelAttribute()
        orig_log_file_path_attrs.set_required(True)
        orig_log_file_path_attrs.set_default(None)
        orig_log_file_path_attrs.set_label('Log File Path')
        orig_log_file_path_attrs.set_type('str')
        orig_log_file_path_attrs.set_is_config_dict_key(True)
        orig_log_file_path_attrs.set_mapped_class_variable('orig_log_file_path')
        self.config_model_attributes['orig_log_file_path'] = orig_log_file_path_attrs

        # Regex to search
        regex_to_search_attrs = AMSConfigModelAttribute()
        regex_to_search_attrs.set_required(True)
        regex_to_search_attrs.set_default(None)
        regex_to_search_attrs.set_label('List of regexes separated by commas (,)')
        regex_to_search_attrs.set_type('list')
        regex_to_search_attrs.set_linked_type('str')
        regex_to_search_attrs.set_mapped_class_variable('regex_to_search')
        regex_to_search_attrs.set_return_transform('str_to_list')
        regex_to_search_attrs.set_return_map_to_variable('regex_to_search')
        self.config_model_attributes['regex_to_search'] = regex_to_search_attrs

    def load(self, log_file_path, config_dict):
        """
        :param log_file_path: full path of log file / pattern from the config dict.
        :type log_file_path: str
        :param config_dict: List of strings to search for
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.orig_log_file_path = log_file_path
            self._read_orig_log_file_path()
            self._read_regex_to_search()
        except AMSLogFileException:
            raise
        except Exception as e:
            raise AMSLogFileException(e)

    def _read_orig_log_file_path(self):
        """
        This method will set the orig_log_file_path variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'orig_log_file_path' in self.raw_config and self.raw_config['orig_log_file_path']:
            self.orig_log_file_path = str(self.raw_config['orig_log_file_path']).strip()

        else:
            self.AMSLogger.critical('orig_log_file_path is not defined for the following log file: ' + self.orig_log_file_path)
            return False

        return True

    def _read_regex_to_search(self):
        """
        This method will set the regex_to_search variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'regex_to_search' in self.raw_config and self.raw_config['regex_to_search']:
            tmp_regex_to_search = self.raw_config['regex_to_search']
            if not isinstance(tmp_regex_to_search, list):
                self.AMSLogger.critical('regex_to_search is not a valid list object in the config for this log file: ' + OutputFormatHelper.join_output_from_list(self.regex_to_search))
                return False

            self.regex_to_search = tmp_regex_to_search
        else:
            self.AMSLogger.critical('regex_to_search is not defined in the config for this log file: ' + self.orig_log_file_path)
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

    def _validate_orig_log_file_path(self, tmp_input):
        if len(tmp_input) == 0:
            return True
        return self._ams_validate_file(tmp_input)