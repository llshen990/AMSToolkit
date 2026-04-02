import abc, os.path, sys, ConfigParser, subprocess, socket

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Exceptions import SsoZabbixWrapperException
from lib.Validators import FileExistsValidator

class AbstractSsoZabbixWrapperHelper(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):

        # defines wrapper script config
        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.abspath(APP_PATH + '/Config/ssod_validator.cfg'))
        self.sso_zabbix_wrapper_script = None
        if self.config.has_option('DEFAULT', 'sso_zabbix_wrapper_script'):
            self.sso_zabbix_wrapper_script = str(self.config.get('DEFAULT', 'sso_zabbix_wrapper_script')).strip()
            fev = FileExistsValidator(True)
            if not fev.validate(self.sso_zabbix_wrapper_script):
                raise SsoZabbixWrapperException(fev.format_errors())
            elif not fev.is_exe(self.sso_zabbix_wrapper_script):
                raise SsoZabbixWrapperException(self.sso_zabbix_wrapper_script + ' is not executable')
        else:
            raise SsoZabbixWrapperException('Config does not contain sso_zabbix_wrapper_script (path to sso zabbix wrapper script)')

        if self.config.has_option('DEFAULT', 'market_config_section'):
            self.project = self.config.get('DEFAULT', 'market_config_section')  # project is an optional flag used to add a project parameter onto the end of a zabbix key. So instead of batch.name, the zabbix key would be batch.name[tst]
        else:
            raise SsoZabbixWrapperException('Config does not contain market_config_section variable')

        self.schedule_name = None  # <schedule_name> is the name of the schedule to be updated
        self.batch_status = None  # Indicates the status of the schedule. You may only specify one value.
        # Primer is used to send initial default values to zabbix. (Schedule name is not valid when primer is used).
        # Primer is also used to reset any flags put into place such as longtime, or multiple jobs.
        self.allowed_batch_status = {
            'start': False, 'stop': False, 'error': False, 'primer': False, 'error-message': False, 'delay-message': False, 'resetmjobs': False
        }
        self.longtime = None  # longtime <minutes> is the time in minutes before your schedule is considered to be running too long.
        self.hostname = socket.getfqdn()  # hostname <hostname> is an optional override of default hostname (default hostname is automatically generated).
        if self.hostname == 'localhost.localdomain':
            self.hostname = None
        self.sigdir = None  # sigdir <signal directory> is an optional override of signal directory. Default is to use environment variable SYSTEM_SIG_DIR
        self.fail = False  # fail is an optional flag used to exit with a status greater than 0 if there is a problem executing commands. Default is to end with a status of 0.
        self.mjobs = False  # mjobs is an optional flag used to keep track of multiple jobs if more than one will be running at the same time.
        self.suffix = None  # suffix is synonymous with -project. -project will take priority though.
        self.priority = None  # priority is an optional flag used to add a priority parameter onto the end of a zabbix key. Requires project to be set.
        self.verbose = False  # v is an optional flag for verbose output.
        self.argument_string_list = [self.sso_zabbix_wrapper_script]  # list of arguments to pass into the zabbix wrapper
        self.error_message = None
        self.delay_message = None
        self.assignee = None
        return

    @abc.abstractmethod
    def set_parameters(self, full_filename, dq_error_txt):
        return

    def _validate_batch_status(self):
        if self.batch_status not in self.allowed_batch_status:
            return False

        return True

    def _add_schedule_arg(self):
        if not self.schedule_name or self.schedule_name == '':
            raise SsoZabbixWrapperException('Zabbix Wrapper Error: Schedule name must be set.')
        self.argument_string_list.append('-s')
        self.argument_string_list.append(self.schedule_name)

        return self

    def _add_batch_status_arg(self):
        if not self.batch_status or self.batch_status == '':
            raise SsoZabbixWrapperException('Zabbix Wrapper Error: Batch status must be set.')

        if not self._validate_batch_status():
            raise SsoZabbixWrapperException('Zabbix Wrapper Error: Invalid batch status ' + self.batch_status + '.  Must be in: ' + ','.join(self.allowed_batch_status))

        self.argument_string_list.append('-' + self.batch_status)

        return self

    def _add_longtime_arg(self):
        # noinspection PyBroadException
        try:
            longtime_int = int(self.longtime)
            if longtime_int > 0:
                self.argument_string_list.append('-longtime')
                self.argument_string_list.append(longtime_int)
        except Exception:
            pass

        return self

    def _add_hostname_arg(self):
        if self.hostname:
            self.argument_string_list.append('-hostname')
            self.argument_string_list.append(self.hostname)

        return self

    def _add_sigdir_arg(self):
        if self.sigdir:
            self.argument_string_list.append('-sigdir')
            self.argument_string_list.append(self.sigdir)

        return self

    def _add_fail_arg(self):
        if self.fail:
            self.argument_string_list.append('-fail')

        return self

    def _add_mjobs_arg(self):
        if self.mjobs:
            self.argument_string_list.append('-mjobs')

        return self

    def _add_project_arg(self):
        if self.project:
            self.argument_string_list.append('-project')
            self.argument_string_list.append(self.project)

        return self

    def _add_suffix_arg(self):
        if self.suffix:
            self.argument_string_list.append('-suffix')
            self.argument_string_list.append(self.suffix)

        return self

    def _add_priority_arg(self):
        if self.priority:
            self.argument_string_list.append('-priority')
            self.argument_string_list.append(self.priority)

        return self

    def _add_verbose_arg(self):
        if self.verbose:
            self.argument_string_list.append('-v')

        return self

    def _construct_arguments(self):
        self._add_schedule_arg()
        self._add_batch_status_arg()
        self._add_longtime_arg()
        self._add_hostname_arg()
        self._add_sigdir_arg()
        self._add_fail_arg()
        self._add_mjobs_arg()
        self._add_project_arg()
        self._add_suffix_arg()
        self._add_priority_arg()
        self._add_verbose_arg()

        return self

    def _execute_zabbix_command(self):
        # print self.argument_string_list
        #
        # print "\n\n"  # @todo: comment line
        # print " ".join(self.argument_string_list)  # @todo: comment line
        # return True  # @todo: comment line

        zabbix_wrapper = subprocess.Popen(self.argument_string_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        zabbix_wrapper_std_out, zabbix_wrapper_std_err = zabbix_wrapper.communicate()

        # print '===================================================='
        # print zabbix_wrapper_std_out
        # print '===================================================='
        if zabbix_wrapper_std_err:
            raise SsoZabbixWrapperException('Error in _execute_zabbix_command(): ' + zabbix_wrapper_std_err.strip())

        return True

    def send_zabbix_message(self):
        self._construct_arguments()._execute_zabbix_command()

    def __del__(self):
        """This is the destructor for DecryptPgP.  It will shred the file i.e. securely delete it."""
        pass