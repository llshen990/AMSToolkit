import sys
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute, AMSCommentable
from Toolkit.Exceptions import AMSLogFileException


class AMSFileHandler(AMSCommentable):
    """
       This class defines the AMSFileHandlers
       """

    def __init__(self):
        # Dynamically import the Defaults module
        # The dependency on AMSDefaults in the Defaults package causes import issues
        # import importlib
        from pydoc import locate
        self.AMSDefaults = locate('Toolkit.Lib.Defaults.AMSDefaults')()
        AMSCommentable.__init__(self)
        self.file_handler_name = None  # type: str
        self.directory_to_watch = None  # type: str
        self.type = None  # type: str
        self.level = None  # type: str
        self.file_pattern = None  # type: str
        self.max_depth = None  # type: int
        self.min_depth = None  # type: int
        self.file_age = None  # type: int
        self.follow_symlinks = None  # type: str
        self.archive_directory = None  # type: str
        self.file_count = None  # type: int

    def get_config_dict_key(self):
        return self.file_handler_name

    def get_static_config_dict_key(self):
        return 'file_handlers'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """
        # File Handler Name
        file_handler_name_attrs = AMSConfigModelAttribute()
        file_handler_name_attrs.set_required(True)
        file_handler_name_attrs.set_default(None)
        file_handler_name_attrs.set_label('File Handler Name')
        file_handler_name_attrs.set_type('str')
        file_handler_name_attrs.set_is_config_dict_key(True)
        file_handler_name_attrs.set_mapped_class_variable('file_handler_name')
        self.config_model_attributes['file_handler_name'] = file_handler_name_attrs

        # File Handler Directory to Watch
        directory_to_watch_attrs = AMSConfigModelAttribute()
        directory_to_watch_attrs.set_required(True)
        directory_to_watch_attrs.set_default(None)
        directory_to_watch_attrs.set_label('Directory to Watch')
        directory_to_watch_attrs.set_type('str')
        directory_to_watch_attrs.set_mapped_class_variable('directory_to_watch')
        self.config_model_attributes['directory_to_watch'] = directory_to_watch_attrs

        # File Handler Type
        type_attrs = AMSConfigModelAttribute()
        type_attrs.set_required(True)
        type_attrs.set_default(None)
        type_attrs.set_options(self.AMSDefaults.file_handler_allowed_types)
        type_attrs.set_label('Type of File Handler')
        type_attrs.set_type('str')
        type_attrs.set_mapped_class_variable('type')
        self.config_model_attributes['type'] = type_attrs

        # File Handler Level
        level_attrs = AMSConfigModelAttribute()
        level_attrs.set_required(True)
        level_attrs.set_default(None)
        level_attrs.set_options(self.AMSDefaults.file_handler_allowed_levels)
        level_attrs.set_label('File Level or Directory Level')
        level_attrs.set_type('str')
        level_attrs.set_mapped_class_variable('level')
        self.config_model_attributes['level'] = level_attrs

        # File Handler File Patterns
        file_pattern_attrs = AMSConfigModelAttribute()
        file_pattern_attrs.set_required(True)
        file_pattern_attrs.set_default(self.AMSDefaults.file_handler_default_file_pattern)
        file_pattern_attrs.set_label('File glob Pattern to Match ')
        file_pattern_attrs.set_linked_type('str')
        file_pattern_attrs.set_mapped_class_variable('file_pattern')
        self.config_model_attributes['file_pattern'] = file_pattern_attrs

        max_depth_attrs = AMSConfigModelAttribute()
        max_depth_attrs.set_required(True)
        max_depth_attrs.set_default(-1)
        max_depth_attrs.set_label('Max Depth (-1 = Infinite)')
        max_depth_attrs.set_type('int')
        max_depth_attrs.set_mapped_class_variable('max_depth')
        self.config_model_attributes['max_depth'] = max_depth_attrs

        min_depth_attrs = AMSConfigModelAttribute()
        min_depth_attrs.set_required(True)
        min_depth_attrs.set_default(0)
        min_depth_attrs.set_label('Min Depth')
        min_depth_attrs.set_type('int')
        min_depth_attrs.set_mapped_class_variable('min_depth')
        self.config_model_attributes['min_depth'] = min_depth_attrs

        file_age_attrs = AMSConfigModelAttribute()
        file_age_attrs.set_required(False)
        file_age_attrs.set_default('')
        file_age_attrs.set_label('File Age in Days')
        file_age_attrs.set_type('int')
        file_age_attrs.set_mapped_class_variable('file_age')
        self.config_model_attributes['file_age'] = file_age_attrs

        file_count_attrs = AMSConfigModelAttribute()
        file_count_attrs.set_required(False)
        file_count_attrs.set_default('0')
        file_count_attrs.set_label('Number of most recent matches to keep')
        file_count_attrs.set_type('int')
        file_count_attrs.set_mapped_class_variable('file_count')
        self.config_model_attributes['file_count'] = file_count_attrs

        follow_symlinks_attrs = AMSConfigModelAttribute()
        follow_symlinks_attrs.set_required(True)
        follow_symlinks_attrs.set_default(self.AMSDefaults.file_handler_default_follow_symlinks)
        follow_symlinks_attrs.set_options(self.AMSDefaults.file_handler_allowed_follow_symlinks)
        follow_symlinks_attrs.set_label('Follow Symlinks?')
        follow_symlinks_attrs.set_type('str')
        follow_symlinks_attrs.set_mapped_class_variable('follow_symlinks')
        self.config_model_attributes['follow_symlinks'] = follow_symlinks_attrs

        archive_directory_attrs = AMSConfigModelAttribute()
        archive_directory_attrs.set_required(True)
        archive_directory_attrs.set_default(self.AMSDefaults.file_handler_default_archive_directory)
        archive_directory_attrs.set_label('Archive Directory')
        archive_directory_attrs.set_type('str')
        archive_directory_attrs.set_mapped_class_variable('archive_directory')
        archive_directory_attrs.set_dependent_variable('type')
        archive_directory_attrs.set_dependent_value('Archive')
        self.config_model_attributes['archive_directory'] = archive_directory_attrs

        AMSCommentable._set_config_model_attributes(self)

    def load(self, file_handler_name, config_dict):
        """
        :param file_handler_name: name of the file handler from the config dict.
        :type file_handler_name: str
        :param config_dict: List of strings to search for
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.file_handler_name = file_handler_name
            self._read_directory_to_watch()
            self._read_type()
            self._read_level()
            self._read_file_pattern()
            self._read_max_depth()
            self._read_min_depth()
            self._read_file_age()
            self._read_file_count()
            self._read_follow_symlinks()
            if self.type in ['Archive']:
                self._read_archive_directory()
            AMSCommentable.load(self)
        except AMSLogFileException:
            raise
        except Exception as e:
            raise AMSLogFileException(e)

    def _read_directory_to_watch(self):
        """
        This method will set the directory_to_watch variable for the file handler.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'directory_to_watch' in self.raw_config and self.raw_config['directory_to_watch']:
            self.directory_to_watch = str(self.raw_config['directory_to_watch']).strip()
        else:
            self.AMSLogger.critical('directory to watch is not defined for the following file handler: ' + self.file_handler_name + '.')

        return True

    def _read_type(self):
        """
        This method will set the type variable for the file handler.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'type' in self.raw_config and self.raw_config['type']:
            self.type = str(self.raw_config['type']).strip()
        else:
            self.AMSLogger.critical('type is not defined for the following file handler: ' + self.file_handler_name + '.')

        return True

    def _read_level(self):
        """
        This method will set the level variable for the file handler.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'level' in self.raw_config and self.raw_config['level']:
            self.level = str(self.raw_config['level']).strip()
        else:
            self.AMSLogger.critical('level is not defined for the following file handler: ' + self.file_handler_name + '.')

        return True

    def _read_file_pattern(self):
        """
        This method will set the file_pattern variable for the file handler.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'file_pattern' in self.raw_config and self.raw_config['file_pattern']:
            self.file_pattern = str(self.raw_config['file_pattern'])
        else:
            self.AMSLogger.critical('file pattern is not defined for the following file handler: ' + self.file_handler_name + '.')

        return True

    def _read_max_depth(self):
        """
        This method will set the max_depth variable for the file handler.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'max_depth' in self.raw_config and self.raw_config['max_depth'] is not None:
            self.max_depth = int(self.raw_config['max_depth'])
        else:
            self.AMSLogger.critical('max depth is not defined for the following file handler: ' + self.file_handler_name + '.')

        return True

    def _read_min_depth(self):
        """
        This method will set the min_depth variable for the file handler.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'min_depth' in self.raw_config and self.raw_config['min_depth'] is not None:
            self.min_depth = int(self.raw_config['min_depth'])
        else:
            self.AMSLogger.critical('min depth is not defined for the following file handler: ' + self.file_handler_name + '.')

        return True

    def _read_file_age(self):
        """
        This method will set the file_age variable for the file handler.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'file_age' in self.raw_config and self.raw_config['file_age'] is not None:
            self.file_age = int(self.raw_config['file_age'])
        else:
            self.AMSLogger.critical('file age is not defined for the following file handler: ' + self.file_handler_name + '.')

        return True

    def _read_file_count(self):
        """
                This method will set the file_count variable for the file handler.
                :return: True upon success or False upon failure.
                :rtype: bool
                """
        if 'file_count' in self.raw_config and self.raw_config['file_count'] is not None:
            self.file_count = int(self.raw_config['file_count'])
        else:
            self.AMSLogger.critical(
                'file count is not defined for the following file handler: ' + self.file_handler_name + '.')

        return True

    def _read_follow_symlinks(self):
        """
        This method will set the follow_symlinks variable for the file handler.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'follow_symlinks' in self.raw_config and self.raw_config['follow_symlinks']:
            self.follow_symlinks = str(self.raw_config['follow_symlinks'])
        else:
            self.AMSLogger.critical('follow symlinks is not defined for the following file handler: ' + self.file_handler_name + '.')

        return True

    def _read_archive_directory(self):
        """
        This method will set the archive_directory variable for the file handler.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'archive_directory' in self.raw_config and self.raw_config['archive_directory']:
            self.archive_directory = str(self.raw_config['archive_directory'])
        else:
            self.AMSLogger.critical('archive directory is not defined for the following file handler: ' + self.file_handler_name + '.')

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

    def _validate_directory_to_watch(self, tmp_input):
        if self._ams_validate_directory(tmp_input) and self._ams_validate_directory_permissions(tmp_input):
            return True

    def _validate_archive_directory(self, tmp_input):
        if self._ams_validate_directory(tmp_input) and self._ams_validate_directory_permissions(tmp_input):
            return True

    def _validate_min_depth(self, tmp_input):
        return self._ams_validate_min_max_depth(tmp_input, self.max_depth)