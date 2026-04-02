import os
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSConfig
from Toolkit.Config import AMSJibbixOptions
from Toolkit.Lib.EventHandlers import AbstractEventHandler
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Lib.Helpers import SASEmail
from lib.Validators import EmailValidator
from lib.Exceptions import EmailException


class AMSEmailEventHandler(AbstractEventHandler):
    def __init__(self, config):
        """
        :param logger: The Logger instance
        :type logger: logger
        :param config: The Config instance
        :type config: AMSConfig
        """
        AbstractEventHandler.__init__(self, config)
        email_validator = EmailValidator(True)
        if not self.config.error_email_to_address or not email_validator.validate(self.config.error_email_to_address):
            self.logger.error('Error email address is not set in global config file or is an invalid email')

    def create(self, options, schedule=None, summary=None, description='None', count=0):
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
        self.options = options

        if summary is not None:
            self.options.summary = summary

        self.message += "\n" + description

        self.message += "\n\n# Generated from host: " + self.config.my_hostname + " from " + self.__class__.__name__ + "\n"

        self.logger.debug('email_to=%s' % self.config.error_email_to_address)
        self.logger.debug('email_subject=%s' % self.options.summary)
        self.logger.debug('email_body=%s' % self.message)
        try:
            sas_email = SASEmail()
            sas_email.set_from(AMSDefaults().from_address)
            sas_email.set_to(self.config.error_email_to_address)
            sas_email.set_subject(self.options.summary)
            sas_email.set_text_message(self.message)
            sas_email.send()
            return True
        except EmailException as e:
            self.logger.error("Error: Email Exception %s" % str(e))
            return False
            # raise
        except Exception as e:
            self.logger.error("Error: Email Exception %s" % str(e))
            self._on_event_handler_fail(e, count+1)
            return False