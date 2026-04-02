import os
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSConfig, AMSMIHealthCheck, AMSSecret, AMSWebScenarioStep, AMSHttpRequest, AMSHttpResponse, AMSConfigModelAttribute
from Toolkit.Models import AbstractAMSConfigCreator

class AMSStpPhaseOneConfigCreator(AbstractAMSConfigCreator):

    def __init__(self, app, hostname, output_folder='/tmp',):
        self.app_service_name = app
        self.AMSConfig = AMSConfig(os.path.join(output_folder, self.app_service_name + ".json"), allow_config_generation=True, always_new=True)
        AbstractAMSConfigCreator.__init__(self, self.AMSConfig)

        # sets and writes config file based on input parameter from excel file
        # *******How do I send a variable to the object so I can use in init?

        self.AMSConfig.error_email_to_address = self.AMSDefaults.default_stp_error_to_email_address
        self.AMSConfig.ams_event_handler = self.AMSDefaults.event_handler
        # ams_config.incoming_dir = AMSDefaults.incoming_dir
        # ams_config.archive_dir = AMSDefaults.archive_dir
        # ams_config.outgoing_dir = AMSDefaults.outgoing_dir
        self.AMSConfig.debug = False
        self.AMSConfig.multi_thread_max_workers = self.AMSDefaults.default_stp_max_workers
        self.AMSConfig.multi_thread_timer_check_interval = self.AMSDefaults.default_stp_thread_timer_check_interval
        my_hostname_attrs = self.AMSConfig.config_model_attributes['my_hostname'] # type: AMSConfigModelAttribute
        my_hostname_attrs.set_include_in_config_file(True)
        self.AMSConfig.config_model_attributes['my_hostname'] = my_hostname_attrs
        self.AMSConfig.my_hostname = hostname
        self.AMSConfig.stp_hostname = hostname
        # ams_config.runbook_link = ""

        # creates a secret object with username and password and writes to config
        self.ams_secret = AMSSecret()
        self.ams_secret.secret_name = "STP"
        self.ams_secret.username = self.AMSDefaults.thycotic_func_username
        self.ams_secret.password = self.AMSDefaults.thycotic_func_password
        self.ams_secret.secret_id = self.AMSDefaults.default_mi_secret_id
        self.ams_secret.domain = ""
        self.AMSConfig.AMSSecrets[self.ams_secret.secret_name] = self.ams_secret
        self.ams_mi_health_checks = None  # type: AMSMIHealthCheck

    def add_mi_healthcheck(self, base_url):
        # creates and adds healthcheck to the config object
        self.AMSConfig.num_ams_mihealthchecks = 1
        self.ams_mi_health_checks = AMSMIHealthCheck()
        self.ams_mi_health_checks.mi_healthcheck_name = self.app_service_name + " MI Health Check"
        self.ams_mi_health_checks.midtier_url = base_url
        self.ams_mi_health_checks.verify_ssl = True
        # self.ams_mi_health_checks.AMSSecret = AMSSecret()
        # self.ams_mi_health_checks.AMSSecret.secret_id = self.AMSDefaults.default_mi_secret_id
        # self.ams_mi_health_checks.AMSSecret.username = self.AMSDefaults.thycotic_func_username
        # self.ams_mi_health_checks.AMSSecret.password = self.AMSDefaults.thycotic_func_password
        self.ams_mi_health_checks.http_proxy = self.AMSDefaults.default_web_proxy
        self.ams_mi_health_checks.https_proxy = self.AMSDefaults.default_web_proxy
        self.ams_mi_health_checks.timeout = self.AMSDefaults.default_timeout
        self.AMSConfig.AMSMIHealthChecks["localhost"] = self.ams_mi_health_checks

    def add_web_scenarios(self, ams_web_scenario):
        self.AMSConfig.num_ams_web_scenarios = 1
        ams_web_scenario.web_scenario_name = self.app_service_name + ' Web_Scenario'
        ams_web_scenario.num_web_scenario_steps = 7

        self.AMSConfig.AMSWebScenarios[ams_web_scenario.web_scenario_name] = ams_web_scenario

    def create_web_scenario_step(self, ams_web_scenario, step_name, url, check_type):
        # creates and adds one web scenario based on the input parameters
        ams_web_scenario_step = AMSWebScenarioStep()

        ams_web_scenario_step.step_name = step_name

        ams_web_scenario_step.AMSHttpRequest = AMSHttpRequest()
        ams_web_scenario_step.AMSHttpResponse = AMSHttpResponse()
        if step_name.lower() == "visual analytics":
            ams_web_scenario_step.AMSHttpRequest.url = url + "/SASVisualAnalyticsHub/"
            ams_web_scenario_step.AMSHttpResponse.regex = ".*/SASVisualAnalyticsHub/Flash/VisualAnalyticsHub\.jsp\?.*|.*Switcher\.gotoApp\('VisualAnalyticsHubLogon'.*"
        elif step_name.lower() == "sas studio":
            ams_web_scenario_step.AMSHttpRequest.url = url + "/SASStudio/"
            ams_web_scenario_step.AMSHttpResponse.regex = ".*workSpaceServerHost.*"  # @todo: add negative match for workspaceConnectionError
        elif step_name.lower() == "sas sna":
            ams_web_scenario_step.AMSHttpRequest.url = url + "/SASSNA"
            ams_web_scenario_step.AMSHttpResponse.regex = ".*<title>SAS Social Network Analysis.*"
        elif step_name.lower() == "sas portal":
            ams_web_scenario_step.AMSHttpRequest.url = url + "/SASPortal/"
            ams_web_scenario_step.AMSHttpResponse.regex = ".*<title>SAS Information Delivery Portal.*"
        elif step_name.lower() == "sas web report studio":
            ams_web_scenario_step.AMSHttpRequest.url = url + "/SASWebReportStudio/"
            ams_web_scenario_step.AMSHttpResponse.regex = ".*<title>SAS Web Report Studio : Welcome to SAS Web Report Studio.*"
        elif step_name.lower() == "sas stored process":
            ams_web_scenario_step.AMSHttpRequest.url = url + "/SASStoredProcess/"
            ams_web_scenario_step.AMSHttpResponse.regex = ".*<title>SAS Stored Process Web Application.*|.*<title>Stored Process Web Application.*"
        elif step_name.lower() == "sas wip services":
            ams_web_scenario_step.AMSHttpRequest.url = url + "/SASWIPServices/"
            ams_web_scenario_step.AMSHttpResponse.regex = ".*The following beans are available for your use.*"
        elif step_name.lower() == "sas logon":
            ams_web_scenario_step.AMSHttpRequest.url = url + "/SASLogon/login"
            ams_web_scenario_step.AMSHttpResponse.regex = ""
        else:
            self.AMSLogger.critical("Invalid Step Name: + " + step_name + " step not written to json file ")
            return
        if check_type == "CN13":
            ams_web_scenario_step.AMSHttpRequest.verify_ssl = "false"

        ams_web_scenario_step.AMSHttpRequest.method = "GET"
        ams_web_scenario_step.AMSHttpRequest.timeout = self.AMSDefaults.default_timeout
        if check_type in ["AWS", 'MI']:
            ams_web_scenario_step.AMSHttpRequest.http_proxy = "http://webproxy.vsp.sas.com:3128"
            ams_web_scenario_step.AMSHttpRequest.https_proxy = "http://webproxy.vsp.sas.com:3128"

        ams_web_scenario_step.AMSHttpResponse.status_code = 200
        ams_web_scenario_step.AMSHttpResponse.header = ""

        ams_web_scenario.AMSWebScenarioSteps[ams_web_scenario_step.get_config_dict_key()] = ams_web_scenario_step