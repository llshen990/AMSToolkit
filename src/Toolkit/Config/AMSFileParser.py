import os
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute, AMSJibbixOptions, AMSCommentable
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Exceptions import AMSLogFileException


class AMSFileParser(AMSCommentable):

    def __init__(self):
        self.AMSDefaults = AMSDefaults()
        AMSCommentable.__init__(self)
        self.file_parser_name = None
        self.base_directory = None
        self.file_pattern = None
        self.max_depth = None
        self.min_depth = None
        self.search_pattern = None
        self.exclude_pattern = None
        self.follow_symlinks = False
        self.on_match_actions = None
        self.AMSJibbixOptions = AMSJibbixOptions()
        self.parser_email_address = None
        self.touch_file = None
        self.clear_signal = None
        self.script = None
        self.confidential_action = None
        self.max_age = -1   # Maximum number of days to search -1 == infinite

    def get_config_dict_key(self):
        return self.file_parser_name

    def get_static_config_dict_key(self):
        return 'file_parsers'

    def _set_config_model_attributes(self):

        # File Parser Name
        file_parser_name_attrs = AMSConfigModelAttribute()
        file_parser_name_attrs.set_required(True)
        file_parser_name_attrs.set_default(None)
        file_parser_name_attrs.set_label('File Parser Name')
        file_parser_name_attrs.set_type('str')
        file_parser_name_attrs.set_is_config_dict_key(True)
        file_parser_name_attrs.set_mapped_class_variable('file_parser_name')
        self.config_model_attributes['file_parser_name'] = file_parser_name_attrs

        # File Parser Base Directory
        base_directory_attrs = AMSConfigModelAttribute()
        base_directory_attrs.set_required(True)
        base_directory_attrs.set_default(None)
        base_directory_attrs.set_label('Base Directory')
        base_directory_attrs.set_type('str')
        base_directory_attrs.set_mapped_class_variable('base_directory')
        self.config_model_attributes['base_directory'] = base_directory_attrs

        # File Parser File Patterns
        file_pattern_attrs = AMSConfigModelAttribute()
        file_pattern_attrs.set_required(True)
        file_pattern_attrs.set_default(self.AMSDefaults.file_parser_default_file_pattern)
        file_pattern_attrs.set_label('File glob Pattern(s) to Match (comma separated)')
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

        # File Parser Search Patterns
        search_pattern_attrs = AMSConfigModelAttribute()
        search_pattern_attrs.set_required(True)
        search_pattern_attrs.set_default(self.AMSDefaults.file_parser_default_search_pattern)
        search_pattern_attrs.set_label('String Pattern to Match (regex)')
        search_pattern_attrs.set_linked_type('str')
        search_pattern_attrs.set_mapped_class_variable('search_pattern')
        self.config_model_attributes['search_pattern'] = search_pattern_attrs

        # File Parser Search Pattern to Exclude
        exclude_pattern_attrs = AMSConfigModelAttribute()
        exclude_pattern_attrs.set_required(False)
        exclude_pattern_attrs.set_default('')
        exclude_pattern_attrs.set_label('String Pattern(s) to Exclude (regex)(comma separated)')
        exclude_pattern_attrs.set_linked_type('str')
        exclude_pattern_attrs.set_mapped_class_variable('exclude_pattern')
        self.config_model_attributes['exclude_pattern'] = exclude_pattern_attrs

        follow_symlinks_attrs = AMSConfigModelAttribute()
        follow_symlinks_attrs.set_required(True)
        follow_symlinks_attrs.set_default(self.AMSDefaults.file_parser_default_follow_symlinks)
        follow_symlinks_attrs.set_label('Follow Symlinks?')
        follow_symlinks_attrs.set_type('bool')
        follow_symlinks_attrs.set_mapped_class_variable('follow_symlinks')
        self.config_model_attributes['follow_symlinks'] = follow_symlinks_attrs

        on_match_actions_attrs = AMSConfigModelAttribute()
        on_match_actions_attrs.set_required(True)
        on_match_actions_attrs.set_default('None')
        on_match_actions_attrs.set_label('Action on match?')
        on_match_actions_attrs.set_type('str')
        on_match_actions_attrs.set_options(self.AMSDefaults.file_parser_action_types)
        on_match_actions_attrs.set_num_required_entries(0)
        on_match_actions_attrs.set_include_in_config_file(True)
        on_match_actions_attrs.set_mapped_class_variable('on_match_actions')
        self.config_model_attributes['on_match_actions'] = on_match_actions_attrs

        confidential_action_attrs = AMSConfigModelAttribute()
        confidential_action_attrs.set_required(True)
        confidential_action_attrs.set_default(False)
        confidential_action_attrs.set_label('Make confidential? (Applies to email and zabbix)')
        confidential_action_attrs.set_type('bool')
        confidential_action_attrs.set_include_in_config_file(True)
        confidential_action_attrs.set_mapped_class_variable('confidential_action')
        self.config_model_attributes['confidential_action'] = confidential_action_attrs

        script_attrs = AMSConfigModelAttribute()
        script_attrs.set_required(True)
        script_attrs.set_label('Full path of script to execute on match')
        script_attrs.set_type('str')
        script_attrs.set_dependent_variable('on_match_actions')
        script_attrs.set_dependent_value('Script')
        script_attrs.set_mapped_class_variable('script')
        self.config_model_attributes['script'] = script_attrs

        clearsignal_attrs = AMSConfigModelAttribute()
        clearsignal_attrs.set_required(True)
        clearsignal_attrs.set_label('Full path of signal file to remove on match')
        clearsignal_attrs.set_type('str')
        clearsignal_attrs.set_dependent_variable('on_match_actions')
        clearsignal_attrs.set_dependent_value('ClearSignal')
        clearsignal_attrs.set_mapped_class_variable('clear_signal')
        self.config_model_attributes['clear_signal'] = clearsignal_attrs

        touch_file_attrs = AMSConfigModelAttribute()
        touch_file_attrs.set_required(True)
        touch_file_attrs.set_label('Full path to touch file location on match')
        touch_file_attrs.set_type('str')
        touch_file_attrs.set_dependent_variable('on_match_actions')
        touch_file_attrs.set_dependent_value('TouchFile')
        touch_file_attrs.set_mapped_class_variable('touch_file')
        self.config_model_attributes['touch_file'] = touch_file_attrs

        on_match_email_attrs = AMSConfigModelAttribute()
        on_match_email_attrs.set_required(True)
        on_match_email_attrs.set_label('Email address(es) for matches (comma separated)')
        on_match_email_attrs.set_type('str')
        on_match_email_attrs.set_dependent_variable('on_match_actions')
        on_match_email_attrs.set_dependent_value('Email')
        on_match_email_attrs.set_mapped_class_variable('parser_email_address')
        self.config_model_attributes['parser_email_address'] = on_match_email_attrs

        # AMSJibbixOptions
        ams_jibbix_options_attrs = AMSConfigModelAttribute()
        ams_jibbix_options_attrs.set_required(False)
        ams_jibbix_options_attrs.set_default(1)
        ams_jibbix_options_attrs.set_max_allowed_entries(1)
        ams_jibbix_options_attrs.set_options([
            1,
            0
        ])
        ams_jibbix_options_attrs.set_label('Set Jibbix Options For This Parser?')
        ams_jibbix_options_attrs.set_type('int')
        ams_jibbix_options_attrs.set_linked_type('Toolkit.Config.AMSJibbixOptions')
        ams_jibbix_options_attrs.set_linked_object('Toolkit.Config.AMSJibbixOptions')
        ams_jibbix_options_attrs.set_linked_label('Jibbix Options for Matches')
        ams_jibbix_options_attrs.set_mapped_class_variable('AMSJibbixOptions')
        ams_jibbix_options_attrs.set_return_map_to_variable('AMSJibbixOptions')
        ams_jibbix_options_attrs.set_dependent_variable('on_match_actions')
        ams_jibbix_options_attrs.set_dependent_value('Zabbix')
        self.config_model_attributes['AMSJibbixOptions'] = ams_jibbix_options_attrs

        # File Parser Max Age
        max_age_attrs = AMSConfigModelAttribute()
        max_age_attrs.set_required(False)
        max_age_attrs.set_default(-1)
        max_age_attrs.set_label('Max Age')
        max_age_attrs.set_type('int')
        max_age_attrs.set_mapped_class_variable('max_age')
        self.config_model_attributes['max_age'] = max_age_attrs

        AMSCommentable._set_config_model_attributes(self)

    def load(self, file_parser_name, config_dict):

        try:
            self.raw_config = config_dict
            self.file_parser_name = file_parser_name
            self._read_string('base_directory')
            self._read_string('file_pattern')
            self._read_string('search_pattern')
            self._read_string('exclude_pattern')
            self._read_int('max_depth')
            self._read_int('min_depth')
            self._read_follow_symlinks()
            self._read_string('on_match_actions')
            self._read_confidential_action()
            if self.on_match_actions == 'Email':
                self._read_string('parser_email_address')
            elif self.on_match_actions == 'TouchFile':
                self._read_string('touch_file')
            elif self.on_match_actions == 'ClearSignal':
                self._read_string('clear_signal')
            elif self.on_match_actions == 'Script':
                self._read_string('script')
            elif self.on_match_actions == 'Zabbix':
                self._read_jibbix_options(self.file_parser_name, self.AMSJibbixOptions)
            self._read_int('max_age')
            AMSCommentable.load(self)

        except AMSLogFileException:
            raise
        except Exception as e:
            raise AMSLogFileException(e)

    def _read_follow_symlinks(self):
        if 'follow_symlinks' in self.raw_config and self.raw_config['follow_symlinks'] is not None:
            self.follow_symlinks = bool(self.raw_config['follow_symlinks'])

    def _read_confidential_action(self):
        if 'confidential_action' in self.raw_config and self.raw_config['confidential_action'] is not None:
            self.confidential_action = bool(self.raw_config['confidential_action'])
        else:
            raise AMSLogFileException('"Confidential Action" is not defined for the following file parser: {}'.format(self.file_parser_name))

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__
