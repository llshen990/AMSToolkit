import os
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSConfig
from Toolkit.Config import AMSJibbixOptions
from Toolkit.Lib.EventHandlers import AbstractEventHandler


class AMSLoggerEventHandler(AbstractEventHandler):
    def __init__(self, config):
        """
        :param logger: The Logger instance
        :type logger: logger
        :param config: The Config instance
        :type config: AMSConfig
        """
        AbstractEventHandler.__init__(self, config)
        self.log_string = '#'*20 + '-LOGGER-' + '#'*20

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
        self.logger.error(self.log_string)
        if summary:
            self.logger.error('summary={}'.format(summary))
        if description:
            self.logger.error('description={}'.format(description))
        if options and options.summary:
            self.logger.error('Ticket summary={}'.format(options.summary))
        if options and options.description:
            self.logger.error('Ticket description={}'.format(options.description))
        self.logger.error(self.log_string)