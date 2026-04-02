import json
from datetime import datetime

from Toolkit.Models import AbstractAMSBase, AMSWebScenarioModel, AMSMIHealthCheckModel
from Toolkit.Config import AMSWebScenario, AMSMIHealthCheck
from Toolkit.Thycotic import AMSSecretServer
from Toolkit.Lib.STP import SASLogin
from Toolkit.Lib import AMSReturnCode, AMSWebReturnCode
from Toolkit.Exceptions import AMSZabbixException, AMSWebScenarioException, AMSConfigException
from Toolkit.Lib.Helpers import AMSZabbix


class STP(AbstractAMSBase):
    def __init__(self, ams_config, use_zabbix=True):
        AbstractAMSBase.__init__(self, ams_config)

        # create a common session for all transactions
        self.sas_login = SASLogin()
        self.username = None
        self.password = None
        self.use_zabbix = use_zabbix

        try:
            # Retrieve the secret from the config
            ams_secret = ams_config.get_secret_by_name('STP')

            if ams_secret.secret_id:
                secret_server = AMSSecretServer(username=self.AMSConfig.decrypt(ams_secret.username), password=self.AMSConfig.decrypt(ams_secret.password), domain=ams_secret.domain, https_proxy=ams_secret.https_proxy)

                self.username = secret_server.get_secret_field(ams_secret.secret_id, 'username')
                self.password = secret_server.get_secret_field(ams_secret.secret_id, 'password')
            else:
                self.username = ams_secret.username
                self.password = ams_secret.password
        except AMSConfigException:
            # This isn't an error if this doesn't exist
            self.AMSLogger.warning("No STP secret exists in the configuration")

    def execute_web_tests(self):
        if self.AMSConfig.num_ams_web_scenarios < 1:
            return None

        result = AMSReturnCode('', True)

        # base_url = ""
        for web_scenario_name, ams_web_scenario in self.AMSConfig.AMSWebScenarios.iteritems():  # type: str, AMSWebScenario
            ams_web_scenario_model = AMSWebScenarioModel(self.AMSConfig, web_scenario_name, self.sas_login.session)

            try:
                try:
                    logon_start_time = datetime.now()
                    first_step = ams_web_scenario_model.get_first_step()
                    self.AMSLogger.debug('First Step URL: %s' % first_step.AMSHttpRequest.url)

                    health_check_id = 'SAS Logon'
                    web_data = [{'{#ID}': health_check_id, '{#HOSTNAME}': self.AMSConfig.stp_hostname, '{#HEALTH_CHECK_NAME}': web_scenario_name}]
                    if self.use_zabbix:
                        zabbix = AMSZabbix(self.AMSLogger, config=self.AMSConfig, hostname=self.AMSConfig.stp_hostname)
                        zabbix.call_zabbix_sender(self.AMSDefaults.zabbix_stp_web_health_check_lld_key, json.dumps({'data': web_data}))

                    # Don't do the sas login if there is none provided
                    if self.username and self.password:
                        ams_web_return_code = self.sas_login.login(first_step.AMSHttpRequest.url, self.AMSConfig.decrypt(self.username), self.AMSConfig.decrypt(self.password))  # type: AMSWebReturnCode
                        test_result = 1
                        logon_message = 'Successfully logged into SAS Logon'
                        if ams_web_return_code.is_error():
                            test_result = 0
                            logon_message = 'SAS Logon failed: %s' % ams_web_return_code.format_errors()

                        ams_web_scenario_model.session = self.sas_login.session

                        if self.use_zabbix and zabbix:
                            zabbix.call_zabbix_sender('synth_trans_web' + '[' + health_check_id + ',httpStatus]', (ams_web_return_code.status_code if ams_web_return_code else '0'))
                            zabbix.call_zabbix_sender('synth_trans_web' + '[' + health_check_id + ',testResult]', str(test_result))
                            zabbix.call_zabbix_sender('synth_trans_web' + '[' + health_check_id + ',message]', logon_message)
                            zabbix.call_zabbix_sender('synth_trans_web' + '[' + health_check_id + ',runTime]', str((datetime.now() - logon_start_time).total_seconds()))

                    # Can't raise an exception here because we need to report that all the endpoints are down due to login failure.
                    # if ams_web_return_code.is_error():
                    #     raise STPException('Failed to login: %s' % ams_web_return_code.format_errors())

                    if first_step.step_name == 'SAS Logon':
                        del ams_web_scenario_model.web_scenario.AMSWebScenarioSteps[first_step.step_name]

                except (AMSZabbixException, AMSWebScenarioException) as e:
                    raise e

                web_scenario_result = ams_web_scenario_model.check_web_scenario()
                print 'Result of web scenario %s is %s' % (str(web_scenario_name), str(web_scenario_result))
                result.add_result(web_scenario_result)

            except (AMSZabbixException, AMSWebScenarioException) as e:
                self.AMSLogger.critical('Failed to update zabbix in web scenario HC: %s' % str(e))
                return None

        # self.AMSLogger.debug('Doing logout...')
        # self.sas_login.logout(base_url)
        return result

    def execute_mi_tests(self):
        if self.AMSConfig.num_ams_mihealthchecks < 1:
            return None

        result = AMSReturnCode('', True)

        for mi_healthcheck_name, mi_healthcheck in self.AMSConfig.AMSMIHealthChecks.iteritems():  # type: str, AMSMIHealthCheck
            ams_mi_health_check_model = AMSMIHealthCheckModel(self.AMSConfig, mi_healthcheck, self.username, self.password)
            mi_health_check_result = ams_mi_health_check_model.check_health(use_zabbix=self.use_zabbix)
            print 'Health of %s is %s' % (str(mi_healthcheck_name), str(mi_health_check_result))
            result.add_result(mi_health_check_result)

        return result