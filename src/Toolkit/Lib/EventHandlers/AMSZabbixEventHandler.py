import os
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSConfig
from Toolkit.Config import AMSJibbixOptions
from Toolkit.Lib.EventHandlers import AbstractEventHandler
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Exceptions import AMSEventHandlerException
from Toolkit.Lib.Defaults import AMSDefaults


class AMSZabbixEventHandler(AbstractEventHandler):
    def __init__(self, config, zabbix_proxy=None, username=None, password=None):
        """
        :param logger: The Logger instance
        :type logger: logger
        :param config: The Config instance
        :type config: AMSConfig
        :param zabbix_proxy: Optional Zabbix proxy hostname
        :type zabbix_proxy: str
        """
        self.ams_defaults = AMSDefaults()
        self.username = username
        self.password = password
        AbstractEventHandler.__init__(self, config)
        self.zabbix = AMSZabbix(self.logger, config, username=self.username, password=self.password, hostname=self.ams_defaults.my_hostname)
        self.zabbix_key = "batch.message"

    def create(self, options, schedule=None, summary=None, description=None, count=0):
        """
        :param options: Loaded AMSJibbixOptions class.
        :type options: AMSJibbixOptions
        :param schedule: The name of the schedule.
        :type schedule: str
        :param summary: Summary of JIRA ticket.
        :type summary: str
        :param description: Text of error will map to JIRA description.
        :type description: str
        :rtype: bool
        :param count: How many attempts have me made to create an event?
        :rtype: int
        """

        if options is None:
            options = self.ams_defaults.AMSJibbixOptions

        self.options = options

        # Use summary if provided
        if summary is not None:
            self.options.summary = summary

        if not self.options.summary:
            raise AMSEventHandlerException('Summary field required in options.')

        # Turn jibbix_options into a string
        self.message = self.options.str_from_options()

        if description is not None:
            self.message += "\n" + description
        elif self.options.description:
            self.message += "\n" + self.options.description

        if schedule is not None:
            key_suffix = "[{0}]".format(schedule)
            zab_key = self.zabbix_key + key_suffix
        else:
            zab_key = self.ams_defaults.default_zabbix_key_no_schedule

        self.logger.debug('zabbix_key=%s' % zab_key)
        self.logger.debug('zabbix_value=%s' % self.message)
        self.logger.debug('sending value for host=%s' % self.zabbix.my_hostname)
        try:
            if not self.zabbix.call_zabbix_sender(zab_key, self.message, force_send=True):
                self.logger.info('Zabbix sender failed, trying fallback...')
                self._on_event_handler_fail(Exception('Zabbix sender failed without an exception - return code false'))
                return False

            return True
        except Exception as e:
            self._on_event_handler_fail(e, count+1)
            return False