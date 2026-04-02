import requests
import json
import re
import traceback
from datetime import datetime

from lib.Validators import ResponseCodeValidator, RegExValidator

from Toolkit.Config import AMSDictEntry, AMSHttpRequest, AMSWebScenarioStep
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from Toolkit.Exceptions import AMSWebScenarioException, AMSZabbixException
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Lib import AMSWebReturnCode


class AMSWebScenarioModel(AbstractAMSBase):
    def __init__(self, ams_config, web_scenario_name, session_object=None):
        AbstractAMSBase.__init__(self, ams_config)
        self.web_scenario = self.AMSConfig.get_web_scenario_by_name(web_scenario_name)  # AMSWebScenario
        # create a common session for all transactions
        if session_object is None:
            self.session = requests.Session()
        elif isinstance(session_object, requests.Session):
            self.session = session_object
        else:
            raise AMSWebScenarioException('Invalid session object specified for session_object in AMSWebScenarioModel::__init__')

        self.AMSConfig.AMSLogger.info('Found web_scenario %s in config' % self.web_scenario.web_scenario_name)

    def _handle_transaction(self, request, response):
        self.AMSConfig.AMSLogger.info('Invoking HTTP method=' + str(request.method) + ' url=' + str(request.url))
        headers = AMSDictEntry.get_dict_entry_array_as_dict(request.headers)
        params = AMSDictEntry.get_dict_entry_array_as_dict(request.params)
        proxies = self._get_proxies_from_request(request)

        http_response = self.session.request(request.method, request.url, verify=request.verify_ssl, params=params, headers=headers, timeout=request.timeout, proxies=proxies)

        # SASStudio only:
        if 'SASStudio' in request.url:
            if http_response.status_code == 200:
                self.AMSLogger.debug('This is SASStudio, requesting sasexec/sessions: %s' % request.url + 'sasexec/sessions')
                http_response = self.session.request('POST', request.url + 'sasexec/sessions', verify=request.verify_ssl, params=params, headers=headers, timeout=request.timeout, proxies=proxies)

        result = AMSWebReturnCode(request.url)
        result.status_code = http_response.status_code
        result.job_success = True

        if response.web_scenario_name is not None:
            self.AMSConfig.AMSLogger.info('Checking HTTP response=' + str(response.status_code))

            if response.status_code is not None:
                validator = ResponseCodeValidator()
                if validator.validate(http_response.status_code, response.status_code):
                    self.AMSConfig.AMSLogger.info('Success status_code=%s matches %s' % (http_response.status_code, response.status_code))
                else:
                    self.AMSConfig.AMSLogger.info('Failure status_code=%s doesn\'t match expected %s' % (http_response.status_code, str(response.status_code)))
                    result.add_error('Response status_code=%s doesn\'t match expected %s' % (http_response.status_code, str(response.status_code)))
                    result.job_success = False

            if response.regex is not None and len(response.regex) > 0:
                validator = RegExValidator(True)
                if validator.validate(http_response.text, response.regex, re.DOTALL):
                    self.AMSConfig.AMSLogger.info('Success response text matches regex=%s' % str(response.regex))
                else:
                    # self.AMSLogger.debug(validator.format_errors())
                    self.AMSConfig.AMSLogger.info('Failure response text doesn\'t match regex=%s' % str(response.regex))
                    if self.AMSConfig.debug:
                        self.AMSConfig.AMSLogger.info('Response text=%s' % http_response.text)
                    result.add_error('Response text doesn\'t match %s' % str(response.regex))
                    result.job_success = False

            if response.header is not None and len(response.header) > 0:
                if response.header in http_response.headers:
                    self.AMSConfig.AMSLogger.info('Success found header=%s' % str(response.header))
                else:
                    self.AMSConfig.AMSLogger.info('Failure response doesn\'t contain header=%s' % str(response.header))
                    if self.AMSConfig.debug:
                        self.AMSConfig.AMSLogger.info('Response headers=%s' % str(http_response.headers))
                    result.add_error('Response doesn\'t contain header=%s' % str(response.header))
                    result.job_success = False
        else:
            self.AMSConfig.AMSLogger.info("WebScenario didn't have a matching response to request=%s" % str(response))
            result.job_success = False

        return result

    @staticmethod
    def _get_proxies_from_request(request):
        """
        Builds proxy list from
        :param request:
        :type request: AMSHttpRequest
        :return: dictionary or None
        :rtype: dict or None
        """
        proxies = None
        if request.http_proxy or request.https_proxy:
            proxies = {}

            if request.http_proxy:
                proxies['http'] = request.http_proxy

            if request.https_proxy:
                proxies['https'] = request.https_proxy

        return proxies

    def get_first_step(self):
        """

        :return: Web scenario Step
        :rtype: AMSWebScenarioStep
        """
        for step_name in self.web_scenario.AMSWebScenarioSteps:
            return self.web_scenario.AMSWebScenarioSteps[step_name]

    def check_web_scenario(self):
        rc = None
        step_number = 0
        reason = None
        test_result = 0

        try:
            for step_name in self.web_scenario.AMSWebScenarioSteps:
                start_time = datetime.now()
                step_number += 1
                step = self.web_scenario.AMSWebScenarioSteps[step_name]

                # TODO: handle LLD
                # nuke any special characters from the scenario_name
                health_check_id = step.step_name

                web_data = [{'{#ID}': health_check_id, '{#HOSTNAME}': self.AMSConfig.stp_hostname, '{#HEALTH_CHECK_NAME}': self.web_scenario.web_scenario_name}]

                if step.AMSHttpRequest.method is None:
                    raise AMSWebScenarioException("No 'request' found")

                try:
                    # TODO: push this constant into AMSDefaults when merged with initial-batch-monitoring
                    zabbix = AMSZabbix(self.AMSLogger, config=self.AMSConfig, hostname=self.AMSConfig.stp_hostname)
                    zabbix.call_zabbix_sender(self.AMSDefaults.zabbix_ams_web_scenario_lld_key, json.dumps({'data': web_data}))

                    self.AMSConfig.AMSLogger.info('Handling transaction')
                    rc = self._handle_transaction(step.AMSHttpRequest, step.AMSHttpResponse)
                except Exception as e:
                    self.AMSLogger.error("Unhandled Exception handling transaction: %s" % str(e))
                    self.AMSLogger.error(traceback.format_exc())

                    rc = AMSWebReturnCode(None)
                    rc.status_code = 408
                    rc.job_success = True
                    reason = str(e)
                    rc.add_error('FAILURE: %s' % reason)
                    self.AMSConfig.AMSLogger.info('FAILURE: %s' % reason)

                finally:
                    result = 'Step ' + str(step_number) + ' - '
                    result += step_name + ' (' + step.AMSHttpRequest.url + ')'

                self.AMSConfig.AMSLogger.info(result)

                if rc and rc.job_success:
                    test_result = 1
                    step_failure_text = 'Webpage check passed.'
                elif reason:
                    step_failure_text = reason
                else:
                    step_failure_text = 'Step ' + str(step_number) + ' - ' + str(self.web_scenario.web_scenario_name) + ': ' + (str(rc.format_errors()) if rc else "")

                # TODO: I'm going to hack in the zabbix calls here.
                # After this is checked in, I'll refactor the caller of this and the webscenario model to return the same returncode
                # and handle the zabbix stuff in the same place in the same manner.
                try:
                    zabbix.call_zabbix_sender('synth_trans' + '[' + health_check_id + ',httpStatus]', (rc.status_code if rc else '0'))
                    zabbix.call_zabbix_sender('synth_trans' + '[' + health_check_id + ',testResult]', str(test_result))
                    zabbix.call_zabbix_sender('synth_trans' + '[' + health_check_id + ',message]', step_failure_text)
                    zabbix.call_zabbix_sender('synth_trans' + '[' + health_check_id + ',runTime]', str((datetime.now() - start_time).total_seconds()))
                except AMSZabbixException as e:
                    self.AMSLogger.critical('Failed to update zabbix for %s: %s' % (self.web_scenario.web_scenario_name, str(e)))

                # If a scenario fails, then break out of the while loop
                # if rc and rc.failed:
                #     break

        except Exception, e:
            raise AMSWebScenarioException('Generic problem handling WebScenario type=' + str(type(e)) + 'e=' + str(e))

        # Always return the result
        return rc
