import sys
import os
import time
from datetime import datetime
from pydoc import locate

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSConfig, AMSJibbixOptions, AMSSchedule
from Toolkit.Lib import AMSReturnCode
from Toolkit.Lib.CompleteHandlers import AbstractCompleteHandler
from Toolkit.Lib.Helpers import AMSUtils
from Toolkit.Thycotic import AMSSecretServer
from Toolkit.Models import AMSSmokeTestModel


class AMSSmokeTestCompleteHandler(AbstractCompleteHandler):
    """
    This class will execute a command on the commandline and return the results.
    """

    def __init__(self, ams_config, ams_complete_handler):
        """
        :param ams_config:
        :type: AMSConfig
        :param ams_complete_handler:
        :type: AMSCompleteHandler
        """
        AbstractCompleteHandler.__init__(self, ams_config, ams_complete_handler)
        self.retry_limit = self.AMSConfig.smoke_test_default_retry_limit
        self.retry_timeout = self.AMSConfig.smoke_test_default_retry_timeout

    def _run_complete_handler(self, schedule, is_success):
        """
        :param schedule:
        :type: AMSSchedule
        :param is_success:
        :type: bool
        This method checks the specified directory and executes the touch command. Returns an AMSReturnCode object.
        :return: AMSReturnCode:
        """
        result = AMSReturnCode()
        result.job_success = True
        complete_time = datetime.now()
        tried_a_test = False

        try:
            for host in self.AMSCompleteHandler.service_params.keys():
                    try:
                        for service in list(self.AMSCompleteHandler.service_params[host]):
                            test = self.AMSCompleteHandler.service_params[host][service]

                            num_retries = 0
                            while True:
                                # find service in environment
                                tried_a_test = True
                                smoketest = locate('Toolkit.Models.AMSSmokeTestModel')(self.AMSConfig, host, service)  # type: AMSSmokeTestModel
                                rval = smoketest.check_health()

                                if test == 'up' and rval == True:
                                    self.AMSLogger.debug('Expected service {} to be {} and it is {}'.format(service, test, test))
                                    break
                                elif test == 'down' and rval == False:
                                    self.AMSLogger.debug('Expected service {} to be {} and it is {}'.format(service, test, test))
                                    break

                                message = 'Expected service {} to be {} on host {} and it is not {}'.format(service, test, host, test)

                                if 0 <= num_retries < self.retry_limit:
                                    num_retries += 1
                                    self.AMSLogger.warning('Attempt #{} {}'.format(num_retries, message))
                                    self.AMSLogger.info('Sleeping {} seconds before retrying the test...'.format(self.retry_timeout))
                                    time.sleep(self.retry_timeout)
                                else:
                                    # if we've tried too many times
                                    self.AMSLogger.error(message)
                                    result.add_error(message)
                                    break

                    except Exception as e:
                        message = 'Problem finding environment for host={} in complete handler {}'.format(host, self.AMSCompleteHandler.complete_handler_name)
                        result.add_error(message)
                        self.AMSLogger.warning('{}: {}'.format(message, e))

        except Exception as E:
            result.job_success = False
            result.add_error(str(E))

        if not tried_a_test:
            result.job_success = False
            result.add_error('No tests are configured')

        # Do jibbix stuff here if this is being executed from a running schedule
        if schedule:
            add_comment_jibbix_options = locate('Toolkit.Config.AMSJibbixOptions')() # type: AMSJibbixOptions
            add_comment_jibbix_options.comment_only = 'true'
            add_comment_jibbix_options.link = 'comm'
            add_comment_jibbix_options.project = schedule.tla
            add_comment_jibbix_options.summary = 'No Summary (comment only)'

            event_handler = self.AMSConfig.ams_attribute_mapper.get_attribute('global_ams_event_handler')

            add_comment_jibbix_options.description = "%s:%s" % (self.AMSConfig.get_my_environment().env_type, os.linesep)
            add_comment_jibbix_options.description += "Schedule %s has completed" % schedule.schedule_name
            if is_success:
                add_comment_jibbix_options.description += " successfully"
            else:
                add_comment_jibbix_options.description += " with errors"

            add_comment_jibbix_options.description += " at %s.%s" % (complete_time.strftime("%Y-%m-%d %H:%M:%S"), os.linesep)
            add_comment_jibbix_options.description += "SmokeTest "

            if result.is_success():
                result.subject = 'SmokeTest successful'
                add_comment_jibbix_options.description += "is successful and services are UP."
            else:
                result.subject = "SmokeTest failed"
                add_comment_jibbix_options.description += "has failed and some services are DOWN.%s%sErrors follow: %s" % (os.linesep, os.linesep, os.linesep)
                add_comment_jibbix_options.description += result.format_errors()

            # Invoke the event handler with None as the schedule name so that the default toolkit.options zabbix item is used
            event_handler.create(add_comment_jibbix_options)
        else:
            if result.is_success():
                self.AMSLogger.info('SmokeTest is successful and services are UP.')
            else:
                self.AMSLogger.info('SmokeTest has failed and some services are DOWN.')
                self.AMSLogger.info("Errors follow:")
                self.AMSLogger.info('{}'.format(result.format_errors()))

        return result

    def instructions_for_verification(self):
        ret_str = 'See the following for triage: %s%s%s' % (self.AMSConfig.AMSDefaults.default_smoketest_jira_link, os.linesep, os.linesep)
        return ret_str
