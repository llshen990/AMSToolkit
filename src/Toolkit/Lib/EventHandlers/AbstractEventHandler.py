import abc
import os
import sys
import traceback
import logging
import importlib

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSJibbixOptions, AMSConfig
from Toolkit.Exceptions import AMSLldException


class AbstractEventHandler(object):
    __metaclass__ = abc.ABCMeta

    @staticmethod
    def create_handler(ams_config):
        try:
            module = importlib.import_module('Toolkit.Lib.EventHandlers.' + ams_config.ams_event_handler + 'EventHandler')
            clazz = getattr(module, ams_config.ams_event_handler + 'EventHandler')
            return clazz(ams_config)
        except:
            return None

    def __init__(self, config):
        """
        :param logger: The Logger instance
        :type logger: AMSLogger
        :param config: The Config instance
        :type config: AMSConfig
        """
        self.logger = logging.getLogger('AMS')
        self.config = config  # type: AMSConfig
        self.message = ""
        self.options = None  # type: AMSJibbixOptions
        self.__bundle_cache = {}
        # @todo: read bundle cache from disk

    @abc.abstractmethod
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
        pass

    def _on_event_handler_fail(self, exception, count=1):
        if count > 1:
            raise AMSLldException('Fallback event handler has also failed.')
        try:
            if self.config.error_email_to_address and self.__whoami != 'AMSEmailEventHandler':
                from Toolkit.Lib.EventHandlers import AMSEmailEventHandler

                summary = "[ERROR] %s" % self.options.summary

                message = "Failure Exception: %s" % str(exception)
                message += "\nFailure Exception Stack Trace: %s" % traceback.format_exc()
                message += "\n---------------------------------------------- Start Original Failure ----------------------------------------------\n\n"
                message += self.message
                message += "\n---------------------------------------------- End Original Failure ------------------------------------------------\n"

                ams_email_event_handler = AMSEmailEventHandler(self.config)
                ams_email_event_handler.create(self.options, summary=summary, description=message, count=count)
            else:
                self.logger.error('Config error_email_to_address is not defined and cannot fallback to email notification on failure')
                raise exception
        except Exception as e:
            self.logger.error('Could not successfully fallback to email notification: %s' % str(e))
            raise

    def _event_bundler(self):
        self.logger.debug('In _event_bundler()')
        if self.options.bundle:
            self.logger.debug('The event bundler is enabled.  bundle=%s | bundle_time=%s' % (self.options.bundle, self.options.bundle_time))
            # @todo: check to see if this alert cache string has been fired in the previous previous time + bundle time < now, fire.

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

    def __del__(self):
        # @todo: write bundle cache to disk
        pass