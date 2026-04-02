import sys
import os
import time
from datetime import datetime
from pydoc import locate

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSConfig, AMSJibbixOptions
from Toolkit.Lib import AMSReturnCode
from Toolkit.Lib.CompleteHandlers import AbstractCompleteHandler


class AMSHealthCheckCompleteHandler(AbstractCompleteHandler):
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
        # Retry twice and wait 300 secs (5 mins) in between retries
        self.retry_limit = 0
        self.retry_timeout = 300

    def _run_complete_handler(self, schedule, is_success):
        """
        This method checks the specified directory and executes the touch command. Returns an AMSReturnCode object.
        :return: AMSReturnCode:
        """
        result = AMSReturnCode()
        result.job_success = True
        complete_time = datetime.now()

        try:
            if self.AMSConfig.my_hostname not in ['ams-toolkit', 'rmss_dummy_host']:
                # We need to deal with disabling proxies or configuring this differently for other proxies
                os.environ["HTTP_PROXY"] = "http://webproxy.vsp.sas.com:3128"
                os.environ["http_proxy"] = "http://webproxy.vsp.sas.com:3128"
                os.environ["HTTPS_PROXY"] = "http://webproxy.vsp.sas.com:3128"
                os.environ["https_proxy"] = "http://webproxy.vsp.sas.com:3128"

            stp = locate('Toolkit.Models.STP')(self.AMSConfig, use_zabbix=False)

            num_retries = 0
            while True:
                mi_result = stp.execute_mi_tests()  # type: AMSReturnCode

                if mi_result and mi_result.is_error():
                    self.AMSLogger.warning("MI Test failed")

                    if 0 <= num_retries < self.retry_limit:
                        self.AMSLogger.warning("MI Test failed.  Going to retry " + str(self.retry_limit - num_retries) + " more times.")
                        num_retries += 1
                        self.AMSLogger.info("Sleeping " + str(self.retry_timeout) + " seconds before trying MI Test...")
                        time.sleep(self.retry_timeout)
                    else:
                        # if we've tried too many times or num_retries is out of range
                        break
                else:
                    # exit the while
                    break

            if mi_result:
                result.add_result(mi_result)

            num_retries = 0
            while True:
                # Similar to stp.py remove the web tests for now
                web_result = stp.execute_web_tests()  # type: AMSReturnCode

                if web_result and web_result.is_error():
                    self.AMSLogger.warning("Web Tests failed")

                    if 0 <= num_retries < self.retry_limit:
                        self.AMSLogger.warning("Web Tests failed.  Going to retry " + str(self.retry_limit - num_retries) + " more times.")
                        num_retries += 1
                        self.AMSLogger.info("Sleeping " + str(self.retry_timeout) + " seconds before trying Web Tests...")
                        time.sleep(self.retry_timeout)
                    else:
                        # if we've tried too many times or num_retries is out of range
                        break
                else:
                    # exit the while
                    break

            if web_result:
                result.add_result(web_result)

        except Exception as E:
            result.job_success = False
            result.add_error(str(E))

        # Do jibbix stuff here
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
        add_comment_jibbix_options.description += "HealthCheck "

        if result.is_success():
            result.subject = 'HealthCheck successful'
            add_comment_jibbix_options.description += "is successful and services are UP."
        else:
            result.subject = "HeathCheck failed"
            add_comment_jibbix_options.description += "has failed and some services are DOWN.%s%sErrors follow:%s" % (os.linesep, os.linesep, os.linesep)
            add_comment_jibbix_options.description += result.format_errors()

        # Invoke the event handler with None as the schedule name so that the default toolkit.options zabbix item is used
        event_handler.create(add_comment_jibbix_options)
        return result

    def instructions_for_verification(self):
        ret_str = 'See the following for triage: %s%s%sVerify the HealthCheck failure by running the following as the run user:%s%setl /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/stp.py --disable_zabbix --config_file=%s' % (self.AMSConfig.AMSDefaults.default_stp_jira_link ,os.linesep, os.linesep, os.linesep, os.linesep, self.AMSConfig.config_path)
        return ret_str
