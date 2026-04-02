import json
import getpass

from Toolkit.Exceptions import AMSConfigException
from Toolkit.Lib.EventHandlers import AMSZabbixEventHandler
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase

class AMSFileRouteLLD(AbstractAMSBase):
    # look at this
    def __init__(self, ams_config, lld_zabbix_key, username=None, password=None, single_route=None):
        """
        This is the initi method to instantiate an AMSRouteFiles object.
        :param ams_config: Loaded AMSConfig object.
        :type ams_config: AMSConfig
        """
        self.username = username
        self.password = password

        AbstractAMSBase.__init__(self, ams_config)
        self.lld_dict = {
            "data": []
        }
        self.all_routes_obj = {}
        # logic split for single file
        try:
            if single_route is not None:
                self.all_routes_obj = self.AMSConfig.get_one_route_for_lld(single_route)
            else:
                self.all_routes_obj = self.AMSConfig.get_all_routes()
        except AMSConfigException as e:
            self.AMSLogger.debug(str(e))
        self.num_routes = len(self.all_routes_obj)
        self.AMSZabbix = AMSZabbix(self.AMSLogger, self.AMSConfig,
                                   username=self.username, password=self.password)
        self.AMSZabbix.retry_limit = -1
        self.lld_zabbix_key = lld_zabbix_key

    def generate_lld_dict(self):
        if self.num_routes < 1:
            return True


        for project_name, route_data_dict in self.all_routes_obj.iteritems():  # type: str, dict
            tmp_dict = dict()
            tmp_dict['{#ROUTE}'] = "fileroute::"+route_data_dict['route_name']
            self.lld_dict['data'].append(tmp_dict)

        return True

    def is_template_applied_to_host(self, zabbix_template, hostname):
        return self.AMSZabbix.is_template_applied(zabbix_template, hostname)

    def apply_template_to_host(self, zabbix_template, hostname):
        return self.AMSZabbix.apply_template_to_host(zabbix_template, hostname)

    def clear_proxy_config_cache(self):
        return self.AMSZabbix.clear_proxy_config_cache()

    def invoke_zabbix_lld(self):
        # next, we will try to determine if the AMS Batch monitoring template is applied to the host.
        self.AMSLogger.debug('LLD JSON: %s' % json.dumps(self.lld_dict, indent=2))
        return self.AMSZabbix.call_zabbix_sender(self.lld_zabbix_key, json.JSONEncoder().encode(self.lld_dict))

    def is_host_in_host_group(self, hostname, host_group_name):
        return self.AMSZabbix.is_host_in_host_group(host_group_name, hostname)

    def add_host_to_host_group(self, hostname, host_group_name):
        return self.AMSZabbix.add_host_to_host_group(host_group_name, hostname)

    def test_zabbix_ticket_generation(self, hostname, username=getpass.getuser()):
        zabbix_event_handler = AMSZabbixEventHandler(self.AMSConfig)
        self.AMSDefaults.AMSJibbixOptions.assignee = username
        # Set the project based on the hostname
        # This is needed because there is no 'jibbix' for LLD and this will ensure the created ticket is created
        # in the correct JIRA project. If we don't do this, then tickets will always be created in the SSO project
        # and consultants don't have access to the SSO project
        if self.AMSDefaults.default_tla:
            self.AMSDefaults.AMSJibbixOptions.project = self.AMSDefaults.default_tla
        self.AMSDefaults.AMSJibbixOptions.labels = 'ams_toolkit, Lev0'
        return zabbix_event_handler.create(self.AMSDefaults.AMSJibbixOptions,
                                           schedule=self.AMSDefaults.default_adhoc_schedule_key,
                                           summary=self.AMSDefaults.test_jira_summary.format(hostname),
                                           description=self.AMSDefaults.test_jira_description)