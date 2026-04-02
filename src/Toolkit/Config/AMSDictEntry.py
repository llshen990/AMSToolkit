import os, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSSecretException
from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute

class AMSDictEntry(AbstractAMSConfig):
    """
       This class defines the markets / environments
       """
    def __init__(self, dict_key='dict_entry'):
        AbstractAMSConfig.__init__(self)
        self.dict_key = dict_key
        self.raw_config = None
        self.key = None  # type: str
        self.value = None  # type: str

    @staticmethod
    def get_dict_entry_array_as_dict(dict_entry_array):
        """
        :param dict_entry_array: Array of AMSDictEntry objects
        :type dict_entry_array: AMSDictEntry[]
        :return: A 'proper' python dictionary representation of key/value pairs
        :rtype: dict[str,str]
        """
        return {key: value.value for (key, value) in dict_entry_array.items()}

    def get_config_dict_key(self):
        return self.key

    def get_static_config_dict_key(self):
        return self.dict_key

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Key
        attrs = AMSConfigModelAttribute()
        attrs.set_required(True)
        attrs.set_default(None)
        attrs.set_label('Key')
        attrs.set_type('str')
        attrs.set_is_config_dict_key(True)
        attrs.set_mapped_class_variable('key')
        self.config_model_attributes['key'] = attrs

        # Value
        attrs = AMSConfigModelAttribute()
        attrs.set_required(True)
        attrs.set_default(None)
        attrs.set_label('Value')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('value')
        self.config_model_attributes['value'] = attrs

    def load(self, key, config_dict):
        """
        :param key: name of the dictionary entry
        :type key: str
        :param config_dict: List of strings to search for
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.key = str(key)
            self._read_value()
        except AMSSecretException:
            raise
        except Exception as e:
            raise AMSSecretException(e)

    def _read_value(self):
        if 'value' in self.raw_config and self.raw_config['value']:
            self.value = str(self.raw_config['value']).strip()
        else:
            self.AMSLogger.critical('value is not defined in the config for this dictionary: ' + self.key)
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