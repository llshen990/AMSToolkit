import logging
import os
import sys
import getpass
from logging.handlers import RotatingFileHandler
from logging import Handler, Formatter
from lib.Validators import FileExistsValidator
from Toolkit.Exceptions import AMSLoggerException
from Toolkit.Lib.Defaults import AMSDefaults

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))


class AMSLogger(Handler):
    """ This class will log messages to a file and send critical and error messages to JIRA.
    """
    logger = logging.getLogger('AMS')

    def __init__(self, log_filename=None, log_path_override=None, debug=False, quiet=False):
        """
        :param log_filename: string
        :param log_path_override: string
        """
        super(AMSLogger, self).__init__()
        self.enable_debug = debug
        self.enable_quiet = quiet
        self.handler = None
        self.handler_debug = None
        self.log_filename_path = None
        self.formatter = None
        self.file_formatter = None

        try:
            running_as_pyinstaller = False
            # To support unit testing we only create handlers if they haven't been previously assigned.
            if AMSLogger.logger is None or len(AMSLogger.logger.handlers) == 0:
                AMSLogger.logger.setLevel(logging.DEBUG)
                AMSLogger.logger.addHandler(self)
                AMSLogger.logger.propagate = False

                # 2018-06-29 17:27:40.915752 [CRITICAL] Outgoing directory does not exist or is not readable: /sso/transport/outgoing
                self.formatter = Formatter(fmt='%(asctime)s [%(levelname)s] %(message)s')
                # 2018-06-29 17:27:40.915752 [CRITICAL] [AMSConfig.py:284] _read_outgoing_dir - Outgoing directory does not exist or is not readable: /sso/transport/outgoing
                self.file_formatter = Formatter(fmt='%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(funcName)s - %(message)s')

                if log_filename is None:
                    log_filename = str(self) + '_' + getpass.getuser()
                else:
                    log_filename = str(log_filename[:-4]).strip() + '__' + getpass.getuser()
                # Running as a pyinstaller bundle
                if 'ETL_LOG_DIR' in os.environ:
                    log_path = os.environ['ETL_LOG_DIR']
                elif getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                    running_as_pyinstaller = True
                    log_path = os.path.join(os.path.expanduser("~"), 'logs')
                elif log_path_override is None:
                    log_path = os.path.join(APP_PATH, 'Toolkit', 'logs')
                else:
                    log_path = str(log_path_override).strip()

                # Attempt to mkdir if doesn't exist for initial condition
                try:
                    os.makedirs(log_path)
                except:
                    # Don't care if it fails or succeeds since the validator will catch this
                    pass

                if not FileExistsValidator.directory_writeable(log_path):
                    raise AMSLoggerException('The following log path is not writeable: %s.' % log_path)

                self.log_filename_path = os.path.join(log_path, log_filename)

                # add a rotating handler
                # 10 x 5M files
                # @todo: these parameters should be configurable?
                self.handler = RotatingFileHandler(self.app_log_filename(), maxBytes=AMSDefaults().logger_default_max_mbytes * 1000 * 1000, backupCount=AMSDefaults().logger_default_backup_count)
                self.handler.formatter = self.file_formatter
                self.handler.setLevel(logging.CRITICAL)

                self.handler_debug = RotatingFileHandler(self.debug_log_filename(), maxBytes=AMSDefaults().logger_default_max_mbytes * 1000 * 1000, backupCount=AMSDefaults().logger_default_backup_count)
                self.handler_debug.setLevel(logging.NOTSET)
                self.handler_debug.formatter = self.file_formatter

                # Add marker before each new invocation
                AMSLogger.logger.info('='*80)
                if not (sys.__stdout__.isatty() or sys.__stdin__.isatty()):
                    self.enable_quiet = True
                    AMSLogger.logger.info('No TTY, suppressing output to stdout/stderr.')
                if running_as_pyinstaller:
                    AMSLogger.logger.info("Running as a pyinstaller bundle")
                else:
                    AMSLogger.logger.info("Running as a normal Python process")
                AMSLogger.logger.info("Logging all application messages to " + self.handler.baseFilename)

                if self.enable_debug:
                    AMSLogger.logger.info("Logging all DEBUG messages to " + self.handler_debug.baseFilename)
            else:
                # Logger already created
                pass

        except Exception as e:
            raise AMSLoggerException(e)

    def emit(self, record):
        try:
            log_message = self.formatter.format(record)

            if record.levelno:
                level = record.levelno
            else:
                level = logging.NOTSET

            if level <= logging.DEBUG:
                if self.enable_debug:
                    output = sys.stdout
                else:
                    output = None
            elif level in [logging.INFO, logging.CRITICAL, logging.WARN]:
                output = sys.stdout
            else:
                output = sys.stderr

            if output and not self.enable_quiet:
                output.write(log_message + os.linesep)

            if not self.send_to_debug(level):
                if self.handler:
                    self.handler.handle(record)
            elif self.enable_debug:
                if self.handler_debug:
                    self.handler_debug.handle(record)

        except Exception as e:
            raise AMSLoggerException(e)

    def set_debug(self, debug):
        if self.enable_debug != debug:
            AMSLogger.logger.info('Set debug enabled to ' + str(debug))
        self.enable_debug = debug

    def set_quiet(self, quiet):
        if self.enable_quiet != quiet:
            AMSLogger.logger.info('Set quiet enabled to ' + str(quiet))
        self.enable_quiet = quiet

    def send_to_debug(self, level):
        # These always go to the DEBUG log
        if level in [logging.DEBUG, logging.CRITICAL]:
            return True
        return False

    def app_log_filename(self):
        return self.log_filename_path + '_app.log'

    def debug_log_filename(self):
        return self.log_filename_path + '_debug.log'

    def debug(self, msg):
        AMSLogger.logger.debug(msg)

    def info(self, msg):
        AMSLogger.logger.info(msg)

    def warning(self, msg):
        AMSLogger.logger.warning(msg)

    def exception(self, msg):
        AMSLogger.logger.critical(msg)

    def error(self, msg):
        AMSLogger.logger.error(msg)

    def critical(self, msg):
        AMSLogger.logger.critical(msg)

    def __str__(self):
        """magic method when you call print({myValidator}) to print the name of the validator"""
        return self.__class__.__name__
