import os
import abc
import sys
import collections
import json
import logging
from pydoc import locate
import socket

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

import Toolkit
from Toolkit.Config import AMSConfigModelAttribute, AMSAttributeMapper
from Toolkit.Exceptions import AMSConfigException, AMSValidationException
from lib.Validators import FileExistsValidator, UrlValidator, EmailValidator


class AbstractAMSConfig(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.__initial_values = collections.OrderedDict()  # type: str, bool
        self.config_model_attributes = collections.OrderedDict()  # type: str, AMSConfigModelAttribute
        self.AMSLogger = logging.getLogger('AMS')
        self.AMSCrypto = locate('Toolkit.Lib.Helpers.AMSCrypto')
        self.my_hostname = str(socket.getaddrinfo(socket.gethostname(), 0, 0, 0, 0, socket.AI_CANONNAME)[0][3]).strip()
        self.debug = False  # type: bool
        self.raw_config = collections.OrderedDict()
        self.fev = FileExistsValidator(True)

        # set the config model attributes
        self._set_config_model_attributes()

        self.ams_attribute_mapper = AMSAttributeMapper()

    @abc.abstractmethod
    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute.  This must be set in each configuration class for the toolkit.
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """
        pass

    @abc.abstractmethod
    def get_config_dict_key(self):
        pass

    @abc.abstractmethod
    def get_static_config_dict_key(self):
        pass

    @abc.abstractmethod
    def load(self, *args):
        pass

    def get_config_attributes(self, member_var):
        """
        This method will return an object representation of the member variable configuration dictionary.
        :param member_var: The member variable you would like to retrieve the configuration for.
        :type member_var: str
        :return: An AMSConfigModelAttribute object.
        :rtype: AMSConfigModelAttribute
        """
        member_var = str(member_var).strip()
        if not member_var:
            raise AMSConfigException('Member variable required to get config model attributes.')

        return self.config_model_attributes[member_var]

    def __read_value(self, key, value=None):
        """
        :param key: key to read from the config dict.
        :type key: str
        :param value: attribute value to set if key is found.
        :type value: dict
        :return: The string value found in the config dict.
        :rtype: str
        """
        if value is None:
            value = key
        if key in self.raw_config:
            setattr(self, value, self.raw_config[key])
        else:
            self.AMSLogger.debug(str(key) + ' is not defined in the config for this config key: ' + str(key))
            return None
        return self.raw_config[key]

    def _read_string(self, key, value=None):
        """
        :param key: key to read from the config dict.
        :type key: str
        :param value: attribute value to set if key is found.
        :type value: dict
        :return: The string value found in the config dict.
        :rtype: str
        """
        rval = self.__read_value(key, value)
        if rval is None:
            return ''
        else:
            return str(rval)

    def _read_int(self, key, value=None):
        """
        :param key: key to read from the config dict.
        :type key: str
        :param value: attribute value to set if key is found.
        :type value: dict
        :return: The int value found in the config dict.
        :rtype: int
        """
        rval = self._read_string(key, value)
        if rval is None:
            return 0
        else:
            try:
                return int(rval)
            except Exception as e:
                if value:
                    self.AMSLogger.warning('Problem converting to int config for this config key: %s.  %s' % (key, str(e)))
                return False

    def _read_bool(self, key, value=None):
        """
        :param key: key to read from the config dict.
        :type key: str
        :param value: attribute value to set if key is found.
        :type value: dict
        :return: The bool value found in the config dict.
        :rtype: bool
        """
        rval = self._read_string(key, value)
        if rval is None:
            return False
        else:
            try:
                return bool(json.loads(rval.lower()))
            except Exception as e:
                if value:
                    self.AMSLogger.warning('Problem converting to bool config for this config key: %s.  Error: %s' % (key, str(e)))
                return False

    def _read_dict(self, key, num_attr):
        """
        This method will set the params dictionary of AMSHttpRequest objects.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        count = 0
        setattr(self, num_attr, count)
        dict_entry = getattr(self, key)
        if key in self.raw_config and self.raw_config[key] and isinstance(self.raw_config[key], dict):
            for name, data in self.raw_config[key].iteritems():
                # create the enty and add to the dictionary
                entry = Toolkit.Config.AMSDictEntry(dict_key=key)
                entry.load(name, data)
                dict_entry[name] = entry
                count += 1

            # set the final updated count
            setattr(self, num_attr, count)

        else:
            self.AMSLogger.debug('No key=%s set in config.' % key)
            return False

        return True

    def _read_debug(self):
        """
        This method will set the debug in the 'global' section of the AMS Config.
        :return: True upon success or false upon failure.
        :rtype: bool
        """
        if 'debug' in self.raw_config:
            tmp_debug = str(self.raw_config['debug']).strip()
            self.debug = True if tmp_debug == "True" else False
        else:
            self.debug = False
            self.AMSLogger.info('debug is not set in config.  Going to set %s based off of global default' % self.debug)

        return True

    def _read_json(self, key):
        """
        :param key: key to read from the config dict.
        :type key: str
        :return: The bool value found in the config dict.
        :rtype: bool
        """
        if not key in self.raw_config:
            return False
        rval = self.raw_config[key]
        if rval is None:
            return False
        else:
            try:
                setattr(self, key, rval)
                return rval

            except Exception as e:
                self.AMSLogger.warning('Problem converting to dict this config key: %s.  Error: %s' % (key, str(e)))
                return False

    def _write_config_section(self, new_config):
        for model_attribute, config_obj in self.config_model_attributes.iteritems():  # type: str, AMSConfigModelAttribute

            if not config_obj.include_in_config_file:
                continue

            if config_obj.linked_object and config_obj.linked_type == 'dict':
                for dynamic_key, dynamic_object in getattr(self, config_obj.return_map_to_variable).iteritems():  # type: str, AbstractAMSConfig
                    if dynamic_object.get_static_config_dict_key() not in new_config:
                        new_config[dynamic_object.get_static_config_dict_key()] = collections.OrderedDict()

                    if dynamic_object.get_config_dict_key() not in new_config[dynamic_object.get_static_config_dict_key()]:
                        new_config[dynamic_object.get_static_config_dict_key()][dynamic_object.get_config_dict_key()] = collections.OrderedDict()

                    new_config[dynamic_object.get_static_config_dict_key()][dynamic_object.get_config_dict_key()] = dynamic_object._write_config_section(collections.OrderedDict())
            elif config_obj.linked_object and config_obj.linked_type == 'list':
                for dynamic_object in getattr(self, config_obj.return_map_to_variable):
                    if dynamic_object.get_static_config_dict_key() not in new_config:
                        new_config[dynamic_object.get_static_config_dict_key()] = list()

                    new_config[dynamic_object.get_static_config_dict_key()].append(dynamic_object._write_config_section(new_config))
            elif config_obj.linked_object:
                dynamic_object = getattr(self, config_obj.mapped_class_variable)  # type: AbstractAMSConfig
                # We cannot write that which does not exist so we should not try. Relates to dependent variables.
                if dynamic_object is not None:
                    new_config[dynamic_object.get_static_config_dict_key()] = dynamic_object._write_config_section(collections.OrderedDict())
            else:
                val = getattr(self, config_obj.mapped_class_variable)
                if val is not None:
                    new_config[model_attribute] = val

        return new_config

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

    # noinspection PyMethodMayBeStatic
    def __get_secret_key(self):
        return "{0: <32}".format('2ldij3204%$#^ESAvljuwA0xlkjsd0').encode("utf-8")

    def pad(self, s):
        return self.AMSCrypto.pad(s)

    def unpad(self, s):
        return self.AMSCrypto.unpad(s)

    def encrypt(self, str_to_encrypt):
        return self.AMSCrypto.encrypt(self.__get_secret_key(), str_to_encrypt)

    def decrypt(self, encrypted_str):
        return self.AMSCrypto.decrypt(self.__get_secret_key(), encrypted_str)

    def _read_jibbix_options(self, item, ams_jibbix_options, key='AMSJibbixOptions', json_key='jibbix_options'):
        """
        This method will set the jibbix attribute for the item by loading the AMSJibbixOptions object.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if json_key in self.raw_config and self.raw_config[json_key]:
            ams_jibbix_options.load(item, self.raw_config[json_key])
        else:
            self.AMSLogger.debug(json_key+' is not defined for the following: ' + item + '.')
            setattr(self, key, None)
            return False

        return True

    def _ams_validate_directory(self, tmp_input):
        fev = FileExistsValidator(self.debug)
        if not fev.directory_exists(tmp_input):
            fev.add_error(tmp_input, 'Directory does not exist')
            raise AMSValidationException(fev.format_errors())

        return True

    def _ams_validate_directory_permissions(self, tmp_input):
        fev = FileExistsValidator(self.debug)
        if not fev.directory_writeable(tmp_input):
            fev.add_error(tmp_input, 'Directory is not writeable')
            raise AMSValidationException(fev.format_errors())
        elif not fev.directory_executable(tmp_input):
            fev.add_error(tmp_input, 'Directory is not executable')
            raise AMSValidationException(fev.format_errors())

        return True

    def _ams_validate_file(self, tmp_input):
        fev = FileExistsValidator(self.debug)
        if not fev.validate(tmp_input):
            raise AMSValidationException(fev.format_errors())

        return True

    def _ams_validate_url(self, tmp_input):
        uv = UrlValidator(self.debug)
        if not uv.validate(tmp_input):
            raise AMSValidationException(uv.format_errors())

        return True

    def _ams_validate_email(self, tmp_input):
        ev = EmailValidator(self.debug)
        if not ev.validate_email_list(tmp_input):
            raise AMSValidationException(ev.format_errors())

        return True

    def _ams_validate_file_name(self, tmp_input):
        fev = FileExistsValidator(self.debug)
        file_name = os.path.basename(tmp_input)
        if file_name in [None, ""]:
            path = tmp_input
        else:
            path = tmp_input[:-len(file_name)]

        if not fev.is_dir(path):
            fev.add_error(os.path.dirname(tmp_input), 'Directory does not exist')
            raise AMSValidationException(fev.format_errors())
        elif not fev.directory_writeable(path):
            fev.add_error(os.path.dirname(tmp_input), 'Directory must be writeable')
            raise AMSValidationException(fev.format_errors())
        elif not fev.directory_exists(tmp_input) or path in [None, '']:
            fev.add_error(tmp_input, 'Must contain a filename')
            raise AMSValidationException(fev.format_errors())
        elif fev.is_dir(tmp_input):
            fev.add_error(tmp_input, 'Invalid File Name, Existing Directory')
            raise AMSValidationException(fev.format_errors())

        return True

    def _ams_validate_min_max_depth(self, tmp_input, max_depth):
        if tmp_input > max_depth and (max_depth != -1):
            raise AMSValidationException('Min Depth is Greater than Max Depth')

        return True
