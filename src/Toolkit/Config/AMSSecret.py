import os, sys, collections
import json

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSSecretException
from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute

class AMSSecret(AbstractAMSConfig):
    """
       This class defines the markets / environments
       """
    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.raw_config = collections.OrderedDict()
        self.secret_name = None  # type: str
        self.secret_id = None  # type: str
        self.username = None  # type: str
        self.password = None  # type: str
        self.domain = None  # type: str
        self.https_proxy = None  # type: str
        self.environment = None # type: str

    def get_config_dict_key(self):
        return self.secret_name

    def get_static_config_dict_key(self):
        return 'secrets'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Secret Name
        attrs = AMSConfigModelAttribute()
        attrs.set_required(True)
        attrs.set_default(None)
        attrs.set_label('Secret Name')
        attrs.set_type('str')
        attrs.set_is_config_dict_key(True)
        attrs.set_mapped_class_variable('secret_name')
        self.config_model_attributes['secret_name'] = attrs

        # Username
        attrs = AMSConfigModelAttribute()
        attrs.set_required(True)
        attrs.set_default(None)
        attrs.set_label('Username')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('username')
        attrs.set_return_transform('encrypt')
        self.config_model_attributes['username'] = attrs

        # Password
        attrs = AMSConfigModelAttribute()
        attrs.set_required(True)
        attrs.set_default(None)
        attrs.set_label('Password')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('password')
        attrs.set_return_transform('encrypt')
        self.config_model_attributes['password'] = attrs

        # Secret Id
        attrs = AMSConfigModelAttribute()
        attrs.set_required(False)
        attrs.set_default(None)
        attrs.set_label('Secret Id (if using Thycotic)')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('secret_id')
        self.config_model_attributes['secret_id'] = attrs

        # Domain
        attrs = AMSConfigModelAttribute()
        attrs.set_required(False)
        attrs.set_default("")
        attrs.set_label('Domain')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('domain')
        self.config_model_attributes['domain'] = attrs

        # Proxy
        attrs = AMSConfigModelAttribute()
        attrs.set_required(False)
        if 'https_proxy' in os.environ:
            attrs.set_default(os.environ['https_proxy'])
        attrs.set_default("")
        attrs.set_label('HTTPS Proxy')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('https_proxy')
        self.config_model_attributes['https_proxy'] = attrs

        # Environment
        attrs = AMSConfigModelAttribute()
        attrs.set_required(False)
        attrs.set_default("")
        attrs.set_label('Environment')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('environment')
        self.config_model_attributes['environment'] = attrs

    def load(self, secret_name, config_dict):
        """
        :param secret_name: name of the secret
        :type secret_name: str
        :param config_dict: List of strings to search for
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self._read_string('secret_name')
            self._read_string('secret_id')
            self._read_string('username')
            self._read_string('password')
            self._read_string('domain')
            self._read_string('https_proxy')
            self._read_string('environment')
        except AMSSecretException:
            raise
        except Exception as e:
            raise AMSSecretException(e)

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass

    def __repr__(self):
        return json.dumps(self.raw_config)
