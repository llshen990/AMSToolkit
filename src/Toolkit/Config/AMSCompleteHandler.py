import sys
import os
import collections

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute, AMSCommentable
from Toolkit.Exceptions import AMSLogFileException, AMSValidationException
from lib.Validators import FileExistsValidator


class AMSCompleteHandler(AMSCommentable):
    """
    This class defines the error/success handlers
    """

    def __init__(self):
        from pydoc import locate
        self.AMSDefaults = locate('Toolkit.Lib.Defaults.AMSDefaults')()
        AMSCommentable.__init__(self)
        self.complete_handler_name = None  # type: str
        self.type = None  # type: str
        self.complete_handler = None  # type: str
        self.schedule_name = None  # type: str
        self.service_params = collections.OrderedDict()

    def get_config_dict_key(self):
        return self.complete_handler_name

    def get_static_config_dict_key(self):
        return 'complete_handlers'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """
        # Complete Handler Name
        complete_handler_name_attrs = AMSConfigModelAttribute()
        complete_handler_name_attrs.set_required(True)
        complete_handler_name_attrs.set_default(None)
        complete_handler_name_attrs.set_label('Complete Handler Name')
        complete_handler_name_attrs.set_type('str')
        complete_handler_name_attrs.set_is_config_dict_key(True)
        complete_handler_name_attrs.set_mapped_class_variable('complete_handler_name')
        self.config_model_attributes['complete_handler_name'] = complete_handler_name_attrs

        # Complete Handler Type
        type_attrs = AMSConfigModelAttribute()
        type_attrs.set_required(True)
        type_attrs.set_default(None)
        type_attrs.set_options(self.AMSDefaults.complete_handler_allowed_types)
        type_attrs.set_label('Type of Complete Handler?')
        type_attrs.set_type('str')
        type_attrs.set_mapped_class_variable('type')
        self.config_model_attributes['type'] = type_attrs

        # Complete Handler
        complete_handler_attrs = AMSConfigModelAttribute()
        complete_handler_attrs.set_required(False)
        complete_handler_attrs.set_default(None)
        complete_handler_attrs.set_label('Full path to Complete Handler file')
        complete_handler_attrs.set_type('str')
        complete_handler_attrs.set_mapped_class_variable('complete_handler')
        self.config_model_attributes['complete_handler'] = complete_handler_attrs

        service_params_attrs = AMSConfigModelAttribute()
        service_params_attrs.set_required(False)
        service_params_attrs.set_label('Service Params Configuration')
        service_params_attrs.set_type('dict')
        service_params_attrs.set_is_config_dict_key(True)
        service_params_attrs.set_allow_edit(False)
        service_params_attrs.set_hide_from_user_display(True)
        service_params_attrs.set_mapped_class_variable('service_params')
        self.config_model_attributes['service_params'] = service_params_attrs

        AMSCommentable._set_config_model_attributes(self)

    def load(self, complete_handler_name, config_dict, schedule_name=None):
        """
        :param complete_handler_name: full path of log file / pattern from the config dict.
        :type complete_handler_name: str
        :param config_dict: List of strings to search for
        :type config_dict: dict
        :param schedule_name : schedule
        :type schedule_name : str
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.complete_handler_name = complete_handler_name
            self.schedule_name = schedule_name
            self._read_type()
            self._read_complete_handler()
            self._read_json('service_params')
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
            self.AMSLogger.critical('type is not defined for the following complete handler: ' + self.complete_handler_name + '.')

        return True

    def _read_complete_handler(self):
        """
        This method will set the complete handler variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'complete_handler' in self.raw_config and self.raw_config['complete_handler']:
            self.complete_handler = str(self.raw_config['complete_handler']).strip()
        else:
            self.AMSLogger.critical('complete handler is not defined for the following complete handler: ' + self.complete_handler_name + '.')

        return True

    def check_complete_handler(self, ams_config, is_success):
        """
        This method will fire off a complete_handler check in a separate thread and monitor the results
        :param ams_config: AMSConfig
        :type ams_config: AMSConfig
        :param is_success: Whether or not the complete handler is a success of failure handler
        :type is_success: bool
        :return: True upon success, false on failure
        :rtype: AMSReturnCode
        """
        self.AMSLogger.debug('In check_complete_handler for %s' % self.complete_handler_name)
        from pydoc import locate
        complete_handler = locate('Toolkit.Lib.CompleteHandlers.'+'AMS' + self.type + 'CompleteHandler')(ams_config, self)  # type: AbstractCompleteHandler
        # set the result message to the commandline output
        result = complete_handler.evaluate_complete_handler(None, is_success)
        result.message = complete_handler.commandline_output()
        return result

    def _validate_complete_handler(self, tmp_input):
        if self.type in ['TouchFile', 'ClearSignal']:
            # validate the directory of the file, not the file itself
            directory = os.path.dirname(tmp_input)
            if directory is not '':
                self.AMSLogger.debug("Validating directory " + directory)
                return self._ams_validate_directory(directory)
            else:
                self.AMSLogger.debug("Using default signal directory for " + self.type + " complete handler")
                return True
        elif self.type in ['Script']:
            script_nm = tmp_input.split()[0]
            fev = FileExistsValidator(self.debug)
            if not fev.validate(script_nm):
                raise AMSValidationException(fev.format_errors())
            elif not fev.is_exe(script_nm):
                fev.add_error(script_nm, 'File is not executable')
                raise AMSValidationException(fev.format_errors())
            return True
        elif self.type in ['STPHealthCheck', 'MIGridServerErrors', 'SmokeTest']:
            # Nothing to validate for this type
            return True
        else:
            # Type was not in the list
            return False

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass
