import abc, os.path, sys, ConfigParser, subprocess, socket
import logging

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Exceptions import SsoZabbixWrapperException
from lib.Validators import FileExistsValidator
from pydoc import locate


class AbstractAMSZabbixWrapperHelper(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):

        # defines wrapper script config
        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.abspath(APP_PATH + '/Config/ssod_validator.cfg'))
        self.sso_zabbix_wrapper_script = None
        self.AMSZabbix = locate('Toolkit.Lib.Helpers.AMSZabbix')(logging.getLogger('AMS'))
        self.AMSDefaults = locate('Toolkit.Lib.Defaults.AMSDefaults')()

        if self.config.has_option('DEFAULT', 'market_config_section'):
            self.project = self.config.get('DEFAULT', 'market_config_section')  # project is an optional flag used to add a project parameter onto the end of a zabbix key. So instead of batch.name, the zabbix key would be batch.name[tst]
        else:
            raise SsoZabbixWrapperException('Config does not contain market_config_section variable')

        self.schedule_name = None  # <schedule_name> is the name of the schedule to be updated
        self.hostname = self.AMSDefaults.my_hostname
        # Primer is used to send initial default values to zabbix. (Schedule name is not valid when primer is used).
        # Primer is also used to reset any flags put into place such as longtime, or multiple jobs.
        self.priority = None  # priority is an optional flag used to add a priority parameter onto the end of a zabbix key. Requires project to be set.
        self.jibbix = locate('Toolkit.Config.AMSJibbixOptions')()
        self.error_message = None
        self.delay_message = None
        self.assignee = None

        return

    @abc.abstractmethod
    def set_parameters(self, full_filename, dq_error_txt):
        return

    def _add_schedule_arg(self):
        if not self.schedule_name or self.schedule_name == '':
            raise SsoZabbixWrapperException('Zabbix Wrapper Error: Schedule name must be set.')
        self.jibbix.schedule_name = self.schedule_name

        return self

    def _add_batch_status_arg(self):
        pass
        return self

    def _add_longtime_arg(self):
        # noinspection PyBroadException
        return self

    def _add_hostname_arg(self):
        return self

    def _add_sigdir_arg(self):
        return self

    def _add_fail_arg(self):
        return self

    def _add_mjobs_arg(self):
        return self

    def _add_project_arg(self):
        self.jibbix.project = self.project

        return self

    def _add_suffix_arg(self):
        pass
        return self

    def _add_priority_arg(self):
        if self.priority:
            self.jibbix.priority = self.priority

        return self

    def _add_verbose_arg(self):
        pass
        return self

    def _execute_zabbix_command(self):
        # print self.argument_string_list
        #
        # print "\n\n"  # @todo: comment line
        # print " ".join(self.argument_string_list)  # @todo: comment line
        # return True  # @todo: comment line
        result = self.AMSZabbix.call_zabbix_sender(self.AMSDefaults.default_zabbix_key_no_schedule, self.jibbix.str_from_options() + os.linesep + self.jibbix.description)

        # print '===================================================='
        # print zabbix_wrapper_std_out
        # print '===================================================='
        if not result:
            raise SsoZabbixWrapperException('Error in _execute_zabbix_command(): ')

        return True

    def send_zabbix_message(self):
        self._execute_zabbix_command()

    def __del__(self):
        """This is the destructor for DecryptPgP.  It will shred the file i.e. securely delete it."""
        pass