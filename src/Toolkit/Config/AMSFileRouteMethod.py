import collections
import os
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSConfigModelAttribute, AbstractAMSConfig
from Toolkit.Exceptions import AMSMethodException, AMSValidationException, AMSValidationExceptionDefault

class AMSFileRouteMethod(AbstractAMSConfig):
    """
        This class defines the markets / environments
    """

    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.raw_config = collections.OrderedDict()
        self.file_route_name = None  # type: str
        self.type = None  # type: str
        self.from_directory = None  # type: str
        self.to_directory = None  # type: str
        self.username = None  # type: str
        self.password = None  # type: str
        self.key_file = None  # type: str
        self.host = None  # type: str
        self.archive_directory = None  # type: str
        self.port = None  # type: int
        self.file_patterns = None  # type: []
        self.overwrite = False
        self.client_id = None  # type: str
        self.secret = None  # type: str
        self.tenant = None  # type: str
        self.store_name = None  # type: str
        self.client_secret = None  # type: str
        self.s3_default_bucket = None  # type: str
        self.to_executable = None  # type: str
        self.on_success_handler_script = None  # type: str
        self.http_proxy = None  # type: str
        self.https_proxy = None  # type: str

    def get_config_dict_key(self):
        return ''

    def get_static_config_dict_key(self):
        return 'method'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """

        # Type
        type_attrs = AMSConfigModelAttribute()
        type_attrs.set_required(True)
        type_attrs.set_default(None)
        type_attrs.set_label('Type')
        type_attrs.set_type('str')
        type_attrs.set_options([
            'SftpPush',
            'SftpPull',
            'Move',
            'ADLSPush',
            'ADLSPull',
            'ElasticsearchPush',
            'S3Push',
            'S3Pull'
        ])
        type_attrs.set_mapped_class_variable('type')
        self.config_model_attributes['type'] = type_attrs

        # From Directory
        from_directory_attrs = AMSConfigModelAttribute()
        from_directory_attrs.set_required(True)
        from_directory_attrs.set_default(None)
        from_directory_attrs.set_label('From Directory')
        from_directory_attrs.set_type('str')
        from_directory_attrs.set_mapped_class_variable('from_directory')
        self.config_model_attributes['from_directory'] = from_directory_attrs

        # To Directory
        to_directory_attrs = AMSConfigModelAttribute()
        to_directory_attrs.set_required(True)
        to_directory_attrs.set_default(None)
        to_directory_attrs.set_label('To Directory')
        to_directory_attrs.set_type('str')
        to_directory_attrs.set_mapped_class_variable('to_directory')
        self.config_model_attributes['to_directory'] = to_directory_attrs

        # File Patterns
        file_patterns_attrs = AMSConfigModelAttribute()
        file_patterns_attrs.set_required(False)
        file_patterns_attrs.set_default('')
        file_patterns_attrs.set_label('List of file regex patterns separated by commas (,)')
        file_patterns_attrs.set_type('list')
        file_patterns_attrs.set_linked_type('str')
        file_patterns_attrs.set_mapped_class_variable('file_patterns')
        file_patterns_attrs.set_return_transform('str_to_list')
        self.config_model_attributes['file_patterns'] = file_patterns_attrs

        # Overwrite
        overwrite_attrs = AMSConfigModelAttribute()
        overwrite_attrs.set_required(False)
        overwrite_attrs.set_default(False)
        overwrite_attrs.set_label('Overwrite destination file if already present')
        overwrite_attrs.set_type('bool')
        overwrite_attrs.set_options([
            True,
            False
        ])
        overwrite_attrs.set_mapped_class_variable('overwrite')
        overwrite_attrs.set_dependent_variable('type')
        overwrite_attrs.set_dependent_value('Move')
        self.config_model_attributes['overwrite'] = overwrite_attrs

        # Archive Directory
        archive_directory_attrs = AMSConfigModelAttribute()
        archive_directory_attrs.set_required(False)
        archive_directory_attrs.set_default(None)
        archive_directory_attrs.set_label('Archive Directory?')
        archive_directory_attrs.set_type('str')
        archive_directory_attrs.set_mapped_class_variable('archive_directory')
        self.config_model_attributes['archive_directory'] = archive_directory_attrs

        # On Success Handler Script
        on_success_handler_script_attrs = AMSConfigModelAttribute()
        on_success_handler_script_attrs.set_required(False)
        on_success_handler_script_attrs.set_default(None)
        on_success_handler_script_attrs.set_label('On Success Handler Script?')
        on_success_handler_script_attrs.set_type('str')
        on_success_handler_script_attrs.set_mapped_class_variable('on_success_handler_script')
        self.config_model_attributes['on_success_handler_script'] = on_success_handler_script_attrs

        # Client ID
        client_attrs = AMSConfigModelAttribute()
        client_attrs.set_required(False)
        client_attrs.set_default(None)
        client_attrs.set_label('Client ID')
        client_attrs.set_type('str')
        client_attrs.set_mapped_class_variable('client_id')
        client_attrs.set_dependent_variable('type')
        client_attrs.set_dependent_value('ADLSPush')
        client_attrs.set_dependent_value('ADLSPull')
        self.config_model_attributes['client_id'] = client_attrs

        # Client Secret
        secret_attrs = AMSConfigModelAttribute()
        secret_attrs.set_required(False)
        secret_attrs.set_default(None)
        secret_attrs.set_label('Client Secret')
        secret_attrs.set_type('str')
        secret_attrs.set_mapped_class_variable('client_secret')
        secret_attrs.set_return_transform('encrypt')
        secret_attrs.set_dependent_variable('type')
        secret_attrs.set_dependent_value('ADLSPush')
        secret_attrs.set_dependent_value('ADLSPull')
        self.config_model_attributes['client_secret'] = secret_attrs

        # Tenant
        tenant_attrs = AMSConfigModelAttribute()
        tenant_attrs.set_required(False)
        tenant_attrs.set_default(None)
        tenant_attrs.set_label('Tenant')
        tenant_attrs.set_type('str')
        tenant_attrs.set_mapped_class_variable('tenant')
        tenant_attrs.set_dependent_variable('type')
        tenant_attrs.set_dependent_value('ADLSPush')
        tenant_attrs.set_dependent_value('ADLSPull')
        self.config_model_attributes['tenant'] = tenant_attrs

        # Store Name
        store_attrs = AMSConfigModelAttribute()
        store_attrs.set_required(False)
        store_attrs.set_default(None)
        store_attrs.set_label('Store Name')
        store_attrs.set_type('str')
        store_attrs.set_mapped_class_variable('store_name')
        store_attrs.set_dependent_variable('type')
        store_attrs.set_dependent_value('ADLSPush')
        store_attrs.set_dependent_value('ADLSPull')
        self.config_model_attributes['store_name'] = store_attrs

        # Username
        username_attrs = AMSConfigModelAttribute()
        username_attrs.set_required(False)
        username_attrs.set_default(None)
        username_attrs.set_label('Username')
        username_attrs.set_type('str')
        username_attrs.set_mapped_class_variable('username')
        username_attrs.set_return_transform('encrypt')
        username_attrs.set_dependent_variable('type')
        username_attrs.set_dependent_value('SftpPush')
        username_attrs.set_dependent_value('SftpPull')
        self.config_model_attributes['username'] = username_attrs

        # Password
        password_attrs = AMSConfigModelAttribute()
        password_attrs.set_required(False)
        password_attrs.set_default(None)
        password_attrs.set_label('Password')
        password_attrs.set_type('str')
        password_attrs.set_mapped_class_variable('password')
        password_attrs.set_return_transform('encrypt')
        password_attrs.set_dependent_variable('type')
        password_attrs.set_dependent_value('SftpPush')
        password_attrs.set_dependent_value('SftpPull')
        self.config_model_attributes['password'] = password_attrs

        # Key File
        key_file_attrs = AMSConfigModelAttribute()
        key_file_attrs.set_required(False)
        key_file_attrs.set_default(None)
        key_file_attrs.set_label('Key File')
        key_file_attrs.set_type('str')
        key_file_attrs.set_mapped_class_variable('key_file')
        key_file_attrs.set_dependent_variable('type')
        key_file_attrs.set_dependent_value('SftpPush')
        key_file_attrs.set_dependent_value('SftpPull')
        self.config_model_attributes['key_file'] = key_file_attrs

        # Host
        host_attrs = AMSConfigModelAttribute()
        host_attrs.set_required(False)
        host_attrs.set_default(None)
        host_attrs.set_label('Host')
        host_attrs.set_type('str')
        host_attrs.set_mapped_class_variable('host')
        host_attrs.set_dependent_variable('type')
        host_attrs.set_dependent_value('SftpPush')
        host_attrs.set_dependent_value('SftpPull')
        self.config_model_attributes['host'] = host_attrs

        # port
        port_attrs = AMSConfigModelAttribute()
        port_attrs.set_required(False)
        port_attrs.set_default(22)
        port_attrs.set_label('Port')
        port_attrs.set_type('int')
        port_attrs.set_mapped_class_variable('port')
        port_attrs.set_dependent_value('SftpPush')
        port_attrs.set_dependent_variable('type')
        port_attrs.set_dependent_value('SftpPull')
        self.config_model_attributes['port'] = port_attrs  # port

        # default_bucket for S3
        s3_default_bucket_attr = AMSConfigModelAttribute()
        s3_default_bucket_attr.set_required(False)
        s3_default_bucket_attr.set_default(None)
        s3_default_bucket_attr.set_label('S3 Default Bucket')
        s3_default_bucket_attr.set_type('str')
        s3_default_bucket_attr.set_mapped_class_variable('s3_default_bucket')
        s3_default_bucket_attr.set_dependent_variable('type')
        s3_default_bucket_attr.set_dependent_value('S3Push')
        s3_default_bucket_attr.set_dependent_value('S3Pull')
        self.config_model_attributes['s3_default_bucket'] = s3_default_bucket_attr

        # Path to Executable
        to_executable_attrs = AMSConfigModelAttribute()
        to_executable_attrs.set_required(False)
        to_executable_attrs.set_default(None)
        to_executable_attrs.set_label('Path to Executable (required for S3 bucket)')
        to_executable_attrs.set_type('str')
        to_executable_attrs.set_mapped_class_variable('to_executable')
        self.config_model_attributes['to_executable'] = to_executable_attrs
        self.config_model_attributes['to_executable'] = to_executable_attrs

        # HTTP Proxy
        attrs = AMSConfigModelAttribute()
        attrs.set_required(False)
        if 'http_proxy' in os.environ:
            attrs.set_default(os.environ['http_proxy'])
        attrs.set_label('HTTP Proxy')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('http_proxy')
        self.config_model_attributes['http_proxy'] = attrs

        # HTTPS Proxy
        attrs = AMSConfigModelAttribute()
        attrs.set_required(False)
        if 'https_proxy' in os.environ:
            attrs.set_default(os.environ['https_proxy'])
        attrs.set_label('HTTPS Proxy')
        attrs.set_type('str')
        attrs.set_mapped_class_variable('https_proxy')
        self.config_model_attributes['https_proxy'] = attrs

    def load(self, file_route_name, config_dict):
        """
        :param file_route_name: file route name from the config dict.
        :type file_route_name: str
        :param config_dict: AMS config dictionary (JSON)
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.file_route_name = file_route_name
            self._read_type()
            self._read_to_directory()
            self._read_from_directory()
            self._read_username()
            self._read_password()
            self._read_bool('overwrite')
            self._read_key_file()
            self._read_host()
            self._read_archive_directory()
            self._read_on_success_handler_script()
            self._read_file_patterns()
            self._read_port()
            self._read_secret()
            self._read_store_name()
            self._read_tenant()
            self._read_client_id()
            self._read_default_bucket()
            self._read_to_executable()
            self._read_string('http_proxy')
            self._read_string('https_proxy')
        except AMSMethodException:
            raise
        except Exception as e:
            raise AMSMethodException(e)

    def _read_type(self):
        """
        This method will set the type variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'type' in self.raw_config and self.raw_config['type']:
            self.type = str(self.raw_config['type']).strip()
        else:
            self.AMSLogger.debug('type is not defined in the config for this file route method: ' + self.file_route_name)
            return False

        return True

    def _read_from_directory(self):
        """
        This method will set the from_directory variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'from_directory' in self.raw_config and self.raw_config['from_directory']:
            self.from_directory = str(self.raw_config['from_directory']).strip()
        else:
            self.AMSLogger.debug('from_directory is not defined in the config for this file route method: ' + self.file_route_name)
            return False

        return True

    def _read_to_directory(self):
        """
        This method will set the to_directory variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'to_directory' in self.raw_config and self.raw_config['to_directory']:
            self.to_directory = str(self.raw_config['to_directory']).strip()
        else:
            self.AMSLogger.debug('to_directory is not defined in the config for this file route method: ' + self.file_route_name)
            return False

        return True

    def _read_username(self):
        """
        This method will set the username variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'username' in self.raw_config and self.raw_config['username']:
            self.username = str(self.raw_config['username']).strip()
        else:
            self.AMSLogger.debug('username is not defined in the config for this file route method: ' + self.file_route_name)
            return False

        return True

    def _read_password(self):
        """
        This method will set the password variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'password' in self.raw_config and self.raw_config['password']:
            self.password = str(self.raw_config['password']).strip()
        else:
            self.AMSLogger.debug('password is not defined in the config for this file route method: ' + self.file_route_name)
            return False

        return True

    def _read_secret(self):
        if 'client_secret' in self.raw_config and self.raw_config['client_secret']:
            self.client_secret = str(self.raw_config['client_secret']).strip()
        else:
            self.AMSLogger.debug('Client secret is not defined in the config for this file route method: ' + self.file_route_name)
            return False
        return True

    def _read_store_name(self):
        if 'store_name' in self.raw_config and self.raw_config['store_name']:
            self.store_name = str(self.raw_config['store_name']).strip()
        else:
            self.AMSLogger.debug('Store name is not defined in the config for this file route method: ' + self.file_route_name)
            return False
        return True

    def _read_tenant(self):
        if 'tenant' in self.raw_config and self.raw_config['tenant']:
            self.tenant = str(self.raw_config['tenant']).strip()
        else:
            self.AMSLogger.debug('Tenant is not defined in the config for this file route method: ' + self.file_route_name)
            return False
        return True

    def _read_client_id(self):
        if 'client_id' in self.raw_config and self.raw_config['client_id']:
            self.client_id = str(self.raw_config['client_id']).strip()
        else:
            self.AMSLogger.debug('client_id is not defined in the config for this file route method: ' + self.file_route_name)
            return False
        return True

    def _read_default_bucket(self):
        if 's3_default_bucket' in self.raw_config and self.raw_config['s3_default_bucket']:
            self.s3_default_bucket = str(self.raw_config['s3_default_bucket']).strip()
        else:
            self.AMSLogger.debug(
                's3_default_bucket is not defined in the config for this file route method: ' + self.file_route_name)
            return False
        return True

    def _read_to_executable(self):
        """
        This method will set the to_executable variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'to_executable' in self.raw_config and self.raw_config['to_executable']:
            self.to_executable = str(self.raw_config['to_executable']).strip()
        else:
            self.AMSLogger.debug('to_executable is not defined in the config for this file route method: ' + self.file_route_name)
            return False

    def _read_key_file(self):
        """
        This method will set the password variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'key_file' in self.raw_config and self.raw_config['key_file']:
            self.key_file = str(self.raw_config['key_file']).strip()
        else:
            self.AMSLogger.debug('key_file is not defined in the config for this file route method: ' + self.file_route_name)
            return False

        return True

    def _read_host(self):
        """
        This method will set the host variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'host' in self.raw_config and self.raw_config['host']:
            self.host = str(self.raw_config['host']).strip()
        else:
            self.AMSLogger.debug('host is not defined in the config for this file route method: ' + self.file_route_name)
            return False

        return True

    def _read_archive_directory(self):
        """
        This method will set the archive_directory variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'archive_directory' in self.raw_config and self.raw_config['archive_directory']:
            self.archive_directory = str(self.raw_config['archive_directory']).strip()
        else:
            self.AMSLogger.debug('archive_directory is not defined in the config for this file route: ' + self.file_route_name)
            return False

        return True

    def _read_on_success_handler_script(self):
        """
        This method will set the on_success_handler_script variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'on_success_handler_script' in self.raw_config and self.raw_config['on_success_handler_script']:
            self.on_success_handler_script = str(self.raw_config['on_success_handler_script']).strip()
        else:
            self.AMSLogger.debug('on_success_handler_script is not defined in the config for this file route: ' + self.file_route_name)
            return False

        return True

    def _read_file_patterns(self):
        """
        This method will set the file_patterns variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'file_patterns' in self.raw_config and self.raw_config['file_patterns']:
            tmp_file_patterns = self.raw_config['file_patterns']
            if not isinstance(tmp_file_patterns, list):
                self.AMSLogger.critical('file_patterns is not a valid list object in the config for this file route: ' + self.file_route_name)
                return False

            self.file_patterns = tmp_file_patterns
        else:
            self.AMSLogger.debug('file_patterns is not defined in the config for this file route: ' + self.file_route_name)
            return False

        return True

    def _read_port(self):
        """
        This method will set the port variable for the project.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'port' in self.raw_config and self.raw_config['port']:
            self.port = int(str(self.raw_config['port']).strip())
        else:
            self.AMSLogger.debug('port is not defined in the config for this file route method: ' + self.file_route_name)
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

    def _validate_from_directory(self, tmp_input):
        if self.type in ['SftpPush', 'Move', 'ADLSPush']:
            return self._ams_validate_directory(tmp_input)
        return True

    def _validate_to_directory(self, tmp_input):
        if self.type in ['SftpPull', 'Move', 'ADLSPull']:
            if self.type in ['Move'] and self.from_directory is not None:
                tmp_path_input = os.path.abspath(tmp_input)
                if tmp_path_input == self.from_directory:
                    self.fev.reset_errors()
                    self.fev.add_error(tmp_input, 'To directory cannot match the From directory')
                    raise AMSValidationException(self.fev.format_errors())
            return self._ams_validate_directory(tmp_input)
        return True

    def _validate_archive_directory(self, tmp_input):
        if len(tmp_input) == 0:
            raise AMSValidationExceptionDefault(value=None)

        return self._ams_validate_directory(tmp_input)

    # commented this out so that we can specify the script like:
    # /home/vagrant/toolkit_env/bin/python <scriptname>
    # def _validate_on_success_handler_script(self, tmp_input):
        # if len(tmp_input) == 0:
        #     return True
        #
        # return self._ams_validate_file(tmp_input)
