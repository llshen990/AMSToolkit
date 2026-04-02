# @author roward
import abc
import os.path
import sys
import ConfigParser
from lib.Helpers import OutputFormatHelper, Logger
from lib.Exceptions import LogException

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../"))
sys.path.append(APP_PATH)


class AbstractScenario:

	def __init__(self, debug=False):
		self.logger = None

		# set debug
		self._debug = True if debug is True else False

		# set some defaults / setup some config data
		self.config = ConfigParser.ConfigParser()
		self.config.read(APP_PATH + '/Config/ssod_validator.cfg')

		default = '/tmp'
		if self.config.has_section('logs_dir'):
			default = self.config.get('DEFAULT', 'logs_dir')

		# Override the Standard Out with our custom Logger
		logfile = str(self) + self.log_name() + '.log'
		self.logger = Logger(os.path.join(default, logfile))
		self.test_mode = None

	def log_name(self):
		return ''

	@abc.abstractmethod
	def run(self):
		return

	def is_debug_enabled(self):
		return self._debug

	def log_it(self, message):
		"""
		If debug is on, will write a message to terminal + log file.  If off, it will only write to log file.
		:param message: Message to write to log.
		:type message: str
		:return: True upon completion
		:rtype: bool
		"""
		try:
			self.logger.write_debug(OutputFormatHelper.log_msg_with_time(message), self._debug)
		except Exception as e:
			raise LogException('log_it exception: ' + str(e))

		return True

	def __str__(self):
		"""magic method when you call print({automation}) to print the name of the automation"""
		return self.__class__.__name__

	def __del__(self):
		"""This is the destructor for all Automations"""
		if self.logger:
			self.logger.close_logger()
		return
