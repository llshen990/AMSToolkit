import argparse
import collections
import termios
import sys
import tty
import readline
from pydoc import locate
import json
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))

from Toolkit.Views import AbstractView
from Toolkit.Config import *
from Toolkit.Exceptions import AMSViewException, AMSAttributeMapperException, AMSAttributeMapperInfoException, AMSValidationException, AMSValidationExceptionDefault
from lib.Helpers import OutputFormatHelper

class CommandLineConfigView(AbstractView):
    """
    Turns a dictionary into a class
    """

    # ----------------------------------------------------------------------
    def __init__(self):
        AbstractView.__init__(self)
        self.parser = argparse.ArgumentParser()
        self.args = None
        self.ams_config = None  # type: AMSConfig()

        self.config_class = None  # type: AbstractAMSConfig
        self.config_model_attribute = None  # type: AMSConfigModelAttribute

        self.config_obj_label = None

        self.__envcfg_red = '\033[0;31m'
        self.__envcfg_yellow = '\033[0;33m'
        self.__envcfg_no_color = '\033[0m'

        self.ams_attribute_mapper = AMSAttributeMapper()

        self.display_only = False
        self.display_only_str = ""
        self.tmp_dict_for_validation = {}

    def get_data(self):
        # noinspection PyTypeChecker
        self.parser.add_argument("--config_file", nargs='?', type=str, default=AMSConfig.get_default_config_path(), help="Config File", required=True)

        try:
            self.args = self.parser.parse_args(self.input_data)
        except Exception as e:
            self.AMSLogger.error("Problem trying to parse arguments: %s" % str(e))
            raise AMSViewException(e)

        self.ams_config = AMSConfig(self.args.config_file, allow_config_generation=True, test_config_path_permissions=True)

    def render(self):
        self.generate_command_line_config_prompts()

    def init(self):
        self.AMSLogger.debug("Start of parsing command line arguments.")
        self.AMSLogger.debug("Command Line Args: {0}".format(self.input_data))
        self.get_data()

    def generate_command_line_config_prompts(self, current_config_object=None, indent_level=0):
        self.config_class = self.ams_config if not current_config_object else current_config_object
        indent_prefix = ""
        if indent_level > 0:
            tmp_indent_num = 0
            while tmp_indent_num < indent_level:
                indent_prefix += "\t"
                tmp_indent_num += 1

        for model_attribute, config_obj in self.config_class.config_model_attributes.iteritems():  # type: str, AMSConfigModelAttribute
            self.config_model_attribute = config_obj
            if config_obj.hide_from_user_display:
                continue
            if config_obj.is_dependent_variable():
                if not config_obj.is_dependency_met(getattr(self.config_class, config_obj.dependent_variable)):
                    if self.display_only:
                        continue
                    # setattr(self.ams_config, config_obj.mapped_class_variable, None)
                    setattr(self.config_class, config_obj.mapped_class_variable, None)
                    continue

            if config_obj.linked_object and config_obj not in ('dict', 'list'):
                self.prompt_command_line_input(indent_prefix)

                if self.display_only:
                    if getattr(self.config_class, config_obj.mapped_class_variable) < 1:
                        continue

                i = 0
                # noinspection PyTypeChecker
                if config_obj.new_value > 0:
                    tmp_new_indent_level = indent_level + 1

                    ret_obj = None
                    if config_obj.type == 'dict':
                        ret_obj = collections.OrderedDict()
                    elif config_obj.type == 'list':
                        ret_obj = list()
                    elif config_obj.linked_type == 'dict':
                        ret_obj = collections.OrderedDict()
                    elif config_obj.linked_type == 'list':
                        ret_obj = list()

                    while i < config_obj.new_value and ((i < config_obj.max_allowed_entries) or (config_obj.max_allowed_entries == -1)):
                        # check and see if we already have an object loaded:
                        try:
                            tmp_loaded_objects = getattr(self.config_class, config_obj.return_map_to_variable)
                            tmp_loaded_objects_len = 0
                            if isinstance(tmp_loaded_objects, dict):
                                tmp_loaded_objects_len = len(list(tmp_loaded_objects.keys()))
                            if isinstance(tmp_loaded_objects, dict) and tmp_loaded_objects_len > 0 and (tmp_loaded_objects_len - 1) >= i:
                                dynamic_object_key = list(tmp_loaded_objects.keys())[i]
                                dynamic_object = tmp_loaded_objects[dynamic_object_key]
                            elif not isinstance(tmp_loaded_objects, (dict, list, str, int)):
                                dynamic_object = tmp_loaded_objects
                            elif config_obj.linked_object not in globals():
                                dynamic_object = locate(config_obj.linked_object)()
                                if isinstance(dynamic_object, AMSDictEntry) and config_obj.linked_type == 'dict' and config_obj.return_map_to_variable is not None:
                                    setattr(dynamic_object, 'dict_key', config_obj.return_map_to_variable)
                            else:
                                dynamic_object = globals()[config_obj.linked_object]()  # type: AbstractAMSConfig
                        except Exception:
                            raise

                        indent_prefix = ""
                        if config_obj.linked_label:
                            if tmp_new_indent_level > 0:
                                tmp_indent_num = 0
                                while tmp_indent_num < tmp_new_indent_level:
                                    indent_prefix += "\t"
                                    tmp_indent_num += 1
                            if not self.display_only:
                                print indent_prefix + '----------------------------- START ' + config_obj.linked_object + ' #' + str(i + 1) + ' -----------------------------'
                                print indent_prefix + config_obj.linked_label
                            else:
                                self.display_only_str += os.linesep + indent_prefix + '----------------------------- START ' + config_obj.linked_object + ' #' + str(i + 1) + ' -----------------------------' + os.linesep
                                self.display_only_str += indent_prefix + config_obj.linked_label + os.linesep

                            self.config_obj_label = config_obj.label

                            if config_obj.linked_type == 'dict':
                                if dynamic_object.__class__.__name__+config_obj.label not in self.tmp_dict_for_validation:
                                    self.tmp_dict_for_validation[dynamic_object.__class__.__name__+config_obj.label] = {}
                            prev_config_class = self.config_class
                            self.generate_command_line_config_prompts(dynamic_object, tmp_new_indent_level)
                            self.config_class = prev_config_class

                        if not self.display_only:
                            self._check_return_transform(config_obj, self.config_class)

                        if config_obj.return_map_to_variable:
                            if config_obj.type == 'list':
                                ret_obj.append(dynamic_object)
                            elif config_obj.linked_type == 'list':
                                ret_obj.append(dynamic_object)
                            elif config_obj.linked_type == 'dict':
                                self.tmp_dict_for_validation[dynamic_object.__class__.__name__+config_obj.label][dynamic_object.get_config_dict_key()] = dynamic_object
                                ret_obj[dynamic_object.get_config_dict_key()] = dynamic_object
                            else:
                                ret_obj = dynamic_object
                        if not self.display_only:
                            print indent_prefix + '----------------------------- END ' + config_obj.linked_object + ' #' + str(i + 1) + ' -------------------------------'
                        else:
                            self.display_only_str += os.linesep + indent_prefix + '----------------------------- END ' + config_obj.linked_object + ' #' + str(i + 1) + ' -------------------------------' + os.linesep
                        i += 1
                    tmp_new_indent_level -= 1
                    if self.display_only:
                        continue

                    # setattr(self.ams_config, config_obj.return_map_to_variable, ret_obj)
                    setattr(self.config_class, config_obj.return_map_to_variable, ret_obj)

                else:
                    # Return an empty object to be written to the JSON
                    # ret_obj = None
                    if config_obj.type == 'dict':
                        ret_obj = collections.OrderedDict()
                    elif config_obj.type == 'list':
                        ret_obj = list()
                    elif config_obj.linked_type == 'dict':
                        ret_obj = collections.OrderedDict()
                    elif config_obj.linked_type == 'list':
                        ret_obj = list()
                    else:
                        # Remove details for AMSJibbixOptions
                        ret_obj = locate(config_obj.linked_object)()

                    # setattr(self.ams_config, config_obj.return_map_to_variable, ret_obj)
                    setattr(self.config_class, config_obj.return_map_to_variable, ret_obj)

            else:
                self.prompt_command_line_input(indent_prefix)
                if not self.display_only:
                    self._check_return_transform(config_obj, self.config_class)
                if self.display_only:
                    continue

                setattr(self.config_class, config_obj.mapped_class_variable, config_obj.new_value)
                # setattr(self.config_class, config_obj.mapped_class_variable, getattr(self.ams_config, config_obj.mapped_class_variable))

    @staticmethod
    def _check_return_transform(config_obj, config_class):
        """
        This method will implement the return transform method specified by the AMSConfigModelAttribute.
        :param config_obj: This is the AMSAttributeMapper object.
        :type config_obj: AMSConfigModelAttribute
        :param config_class: This is an extension of AbstractAMSConfig.
        :type config_class: AbstractAMSConfig
        :return: True upon success.
        :rtype: bool
        """
        if config_obj.return_transform:
            if config_obj.return_transform == 'str_to_list':
                new_list_tmp = str(config_obj.new_value).split(',')
                new_list = []
                for val in new_list_tmp:
                    new_list.append(str(val).strip())

                config_obj.new_value = new_list
            elif config_obj.return_transform == 'str_to_tuple':
                new_list_tmp = str(config_obj.new_value).split(',')
                new_list = []
                for val in new_list_tmp:
                    new_list.append(str(val).strip())

                config_obj.new_value = new_list
            elif config_obj.return_transform == 'encrypt':
                config_obj.new_value = config_class.encrypt(config_obj.new_value)
            elif config_obj.return_transform == 'abspath':
                config_obj.new_value = os.path.abspath(config_obj.new_value)
        return True

    def prompt_command_line_input(self, indent_prefix=''):
        input_default_from_outer_config = None
        try:
            input_default_from_outer_config = self.ams_attribute_mapper.get_attribute(self.config_model_attribute.mapped_class_variable)
        except AMSAttributeMapperInfoException:
            self.AMSLogger.debug('Could not find attribute in AMSAttributeMapper: %s' % self.config_model_attribute.mapped_class_variable)
        except AMSAttributeMapperException:
            self.AMSLogger.debug('Could not get AMSAttributeMapper attribute of: %s' % self.config_model_attribute.mapped_class_variable)

        if (self.display_only and self.config_model_attribute.linked_object is not None) or (self.config_model_attribute.linked_object == self.config_model_attribute.linked_type and self.config_model_attribute.max_allowed_entries == 1 and self.config_model_attribute.default == 1):
            loaded_class = getattr(self.config_class, self.config_model_attribute.mapped_class_variable)
            if isinstance(loaded_class, int):
                current_value = loaded_class
            elif loaded_class is None:
                current_value = 0
            else:
                if len(loaded_class.raw_config) > 0:
                    current_value = 1
                else:
                    current_value = 0

            # if getattr(self.config_class, self.config_model_attribute.mapped_class_variable):
            #     current_value = 1
            # else:
            #     current_value = 0
        elif getattr(self.config_class, self.config_model_attribute.mapped_class_variable) is not None:
            current_value = getattr(self.config_class, self.config_model_attribute.mapped_class_variable)
            if self.config_model_attribute.return_transform == 'str_to_list' and isinstance(current_value, list):
                current_value = ",".join(current_value)
            elif self.config_model_attribute.return_transform == 'encrypt':
                try:
                    current_value = self.config_class.decrypt(current_value)
                except:
                    # If the value fails to decrypt, then instead of throwing an unchecked error, set current_value to empty string
                    current_value = ''
            # else:
            #     current_value = self.config_model_attribute.default
        else:
            current_value = None

        if input_default_from_outer_config:  # or current_value:
            default_value = input_default_from_outer_config
        else:
            default_value = self.config_model_attribute.default
            if not self.display_only and AMSAttributeMapper().is_set_attribute('home_dir') and default_value == AMSProject().default_signal_dir:
                default_value = os.path.abspath(AMSAttributeMapper().get_attribute('home_dir') + default_value)

        if default_value is None:
            if self.config_model_attribute.type in ['int', 'list', 'dict']:
                default_value = 0
            elif self.config_model_attribute.type == 'str':
                default_value = ''

        # Handle linked objects
        if (self.display_only and self.config_model_attribute.linked_object is not None) or (self.config_model_attribute.required == 1 and self.config_model_attribute.max_allowed_entries == 1 and self.config_model_attribute.default == 1 and self.config_model_attribute.linked_object == self.config_model_attribute.linked_type):
            self.config_model_attribute.new_value = 1
            return self.config_model_attribute.new_value
        # if the field is required
        if self.config_model_attribute.required:
            indent_prefix = indent_prefix + '(*) '
        if self.config_model_attribute.return_transform == "encrypt":
            encrypted = True
        else:
            encrypted = False

        self.config_model_attribute.new_value = self._prompt_for_input(default_value, current_value, indent_prefix, encrypted)

        if self.config_model_attribute.share_value:
            try:
                self.ams_attribute_mapper.set_attribute(self.config_model_attribute.mapped_class_variable, self.config_model_attribute.new_value, True)
            except AMSAttributeMapperException:
                self.AMSLogger.debug('Could not set AMSAttributeMapper attribute of: %s' % self.config_model_attribute.mapped_class_variable)

        return self.config_model_attribute.new_value

    def _prompt_for_input(self, default_value, current_value, indent_prefix='', encrypted=False):
        raw_input_tmp = self._display_to_user(default_value, current_value, indent_prefix, encrypted)
        if not self.display_only:
            raw_input_tmp = self._validate_user_input_type(raw_input_tmp, default_value, current_value, indent_prefix)
            raw_input_tmp = self._validate_config_dict_key(raw_input_tmp, default_value, current_value, indent_prefix)
            raw_input_tmp = self._validate_required(raw_input_tmp, default_value, current_value, indent_prefix)
            raw_input_tmp = self._validate_options(raw_input_tmp, default_value, current_value, indent_prefix)
            raw_input_tmp = self._internal_validation(raw_input_tmp, default_value, current_value, indent_prefix)

        return raw_input_tmp

    def read_input(self, prompt, prefill=None):
        if self.display_only:
            if self.display_only_str:
                self.display_only_str += "\n"

            self.display_only_str += prompt

            if prefill is not None:
                self.display_only_str += " " + str(prefill)

        else:
            if prefill is not None:
                readline.set_startup_hook(lambda: readline.insert_text(str(prefill)))
            try:
                return raw_input(prompt).strip()
            finally:
                if prefill is not None:
                    readline.set_startup_hook()

    def _display_to_user(self, default_value, current_value, indent_prefix, encrypted=False):
        if self.config_model_attribute.return_transform == "encrypt":
            encrypted = True
        if self.display_only:
            if encrypted:
                return '*******'
                # return self._getpass(indent_prefix + str(self.config_model_attribute.label) + ': ')
            elif (not current_value and self.config_model_attribute.type != 'bool' and current_value != 0) or current_value is None:
                return self.read_input(indent_prefix + str(self.config_model_attribute.label) + ': ', default_value)
            elif default_value in (None, ''):
                return self.read_input((indent_prefix + str(self.config_model_attribute.label) + ': '), current_value)
            else:
                return self.read_input((indent_prefix + str(self.config_model_attribute.label) + ' [%s]: ') % default_value, current_value)
        else:
            if encrypted:
                return self._getpass(self.__envcfg_yellow + indent_prefix + str(self.config_model_attribute.label) + ': ' + self.__envcfg_no_color, current_value)
            elif (not current_value and self.config_model_attribute.type != 'bool' and current_value != 0) or current_value is None:
                return self.read_input(self.__envcfg_yellow + indent_prefix + str(self.config_model_attribute.label) + ': ' + self.__envcfg_no_color, default_value)
            elif default_value in (None, ''):
                return self.read_input((self.__envcfg_yellow + indent_prefix + str(self.config_model_attribute.label) + ': ' + self.__envcfg_no_color), current_value)
            elif self.ams_config.new_config and self.config_model_attribute.type == 'int' and default_value == 1:
                return self.read_input((self.__envcfg_yellow + indent_prefix + str(self.config_model_attribute.label) + ' [%s]: ' + self.__envcfg_no_color) % default_value, default_value)
            else:
                return self.read_input((self.__envcfg_yellow + indent_prefix + str(self.config_model_attribute.label) + ' [%s]: ' + self.__envcfg_no_color) % default_value, current_value)

    def _validate_user_input_type(self, raw_input_tmp, default_value, current_value, indent_prefix, return_on_exception=False):
        passed_type_validation = False
        while not passed_type_validation:
            if self.config_model_attribute.type in ['str', 'bool', 'int']:
                try:
                    if self.config_model_attribute.type is 'bool':
                        if raw_input_tmp == '' and not self.config_model_attribute.required:
                            raw_input_tmp = False

                        raw_input_tmp = json.loads(str(raw_input_tmp).lower())
                    else:
                        if self.config_model_attribute.type is 'int':
                            if raw_input_tmp == '' and not self.config_model_attribute.required:
                                raw_input_tmp = False
                        raw_input_tmp = globals()['__builtins__'][self.config_model_attribute.type](raw_input_tmp)
                    passed_type_validation = True
                except Exception as e:
                    print indent_prefix + self.__envcfg_red + ('[ERROR] Failed type validation: %s' + self.__envcfg_no_color) % str(e)
                    # passed_type_validation = False
                    raw_input_tmp = self._display_to_user(default_value, current_value, indent_prefix)
                    # raw_input_tmp = self._validate_user_input_type(raw_input_tmp, default_value, current_value, indent_prefix)
                    if return_on_exception:
                        return raw_input_tmp
            else:
                passed_type_validation = True

        return raw_input_tmp

    def _validate_required(self, raw_input_tmp, default_value, current_value, indent_prefix):
        if self.config_model_attribute.required:
            if self.config_model_attribute.options and not raw_input_tmp:
                print indent_prefix + self.__envcfg_red + '[VALID OPTIONS] ' + self.config_model_attribute.label + ': ' + os.linesep + indent_prefix + OutputFormatHelper.join_output_from_list(self.config_model_attribute.options, os.linesep + indent_prefix) + self.__envcfg_no_color

            # if not raw_input_tmp and self.config_model_attribute.default is not False:
            if not raw_input_tmp and raw_input_tmp != 0 and self.config_model_attribute.default is not False and self.config_model_attribute.default != 0:
                print indent_prefix + self.__envcfg_red + '[REQUIRED] ' + self.config_model_attribute.label + self.__envcfg_no_color
                raw_input_tmp = self._prompt_for_input(default_value, current_value, indent_prefix)

        return raw_input_tmp

    def _validate_options(self, raw_input_tmp, default_value, current_value, indent_prefix):

        if self.config_model_attribute.options and raw_input_tmp:
            if not raw_input_tmp in self.config_model_attribute.options:
                print indent_prefix + self.__envcfg_red + '[INVALID] ' + self.config_model_attribute.label + ': ' + os.linesep + indent_prefix + OutputFormatHelper.join_output_from_list(self.config_model_attribute.options, os.linesep + indent_prefix) + self.__envcfg_no_color
                raw_input_tmp = self._prompt_for_input(default_value, current_value, indent_prefix)

        return raw_input_tmp

    def _validate_config_dict_key(self, raw_input_tmp, default_value, current_value, indent_prefix):
        if self.config_model_attribute is not None and self.config_model_attribute.is_config_dict_key:
            if self.config_obj_label is None:
                tmp_class_name = self.config_class.__class__.__name__
            else:
                tmp_class_name = self.config_class.__class__.__name__ + self.config_obj_label
            if tmp_class_name in self.tmp_dict_for_validation:
                if raw_input_tmp in self.tmp_dict_for_validation[tmp_class_name]:
                    print indent_prefix + self.__envcfg_red + '[DUPLICATE KEY] ' + self.config_model_attribute.label + ': %s%s' % (
                    raw_input_tmp, self.__envcfg_no_color)
                    raw_input_tmp = self._prompt_for_input(default_value, current_value, indent_prefix)

        return raw_input_tmp

    def _internal_validation(self, raw_input_tmp, default_value, current_value, indent_prefix):
        val_check_outcome = False
        item_to_validate = ''
        if self.config_model_attribute is not None:
            item_to_validate = "_validate_" + self.config_model_attribute.mapped_class_variable
        while not val_check_outcome:
            try:
                if hasattr(self.config_class, item_to_validate):
                    val_check_outcome = getattr(self.config_class, item_to_validate)(raw_input_tmp)

                    if not val_check_outcome:
                        print indent_prefix + self.__envcfg_red + '[INVALID Entry] '
                        raw_input_tmp = self._display_to_user(default_value, raw_input_tmp, indent_prefix)
                else:
                    val_check_outcome = True
            except AMSValidationException as e:
                print indent_prefix + self.__envcfg_red + '[INVALID] %s ' % str(e)
                raw_input_tmp = self._prompt_for_input(default_value, raw_input_tmp, indent_prefix)
            except AMSValidationExceptionDefault as e:
                print indent_prefix + self.__envcfg_yellow + '[WARN] Restoring default value'
                return e.value
            except Exception as e:
                print indent_prefix + self.__envcfg_red + '[Error] %s' % str(e)
                raw_input_tmp = self._display_to_user(default_value, raw_input_tmp, indent_prefix)
            raw_input_tmp = self._validate_user_input_type(raw_input_tmp, default_value, current_value, indent_prefix)

        return raw_input_tmp

    @staticmethod
    def _getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def _getpass(self, prompt, fill):
        sys.stdout.write(prompt)
        if fill:
            sys.stdout.write('*'*len(fill))
            buf = fill
        else:
            buf = ''
        count = 0
        if fill is not None:
            count = len(fill)
        while True:
            ch = self._getch()

            if ord(ch) == 13:
                # Enter
                print('')
                break
            elif ord(ch) == 3:
                # ^C
                sys.exit()
            elif ord(ch) == 21:
                # Ctrl + U
                for i in range(count):
                    sys.stdout.write('\b \b')
                    buf = buf[:-1]
                    i -= 1
                count = 0
            elif ord(ch) == 127 or ord(ch) == 8:
                # Backspace
                if count == 0:
                    continue
                else:
                    sys.stdout.write('\b \b')
                    buf = buf[:-1]
                    count -= 1
            else:
                buf += ch
                sys.stdout.write('*')
                count += 1
        return buf