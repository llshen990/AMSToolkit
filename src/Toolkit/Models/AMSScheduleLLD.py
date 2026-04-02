import json
import getpass

from Toolkit.Exceptions import AMSConfigException
from Toolkit.Lib.EventHandlers import AMSZabbixEventHandler
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase

class AMSScheduleLLD(AbstractAMSBase):
    # look at this
    def __init__(self, ams_config, lld_zabbix_key, username=None, password=None, single_schedule=None):
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
        self.all_schedules_obj = {}
        # logic split for single file
        try:
            if single_schedule is not None:
                self.all_schedules_obj = self.AMSConfig.get_one_schedule_for_lld(single_schedule)
            else:
                self.all_schedules_obj = self.AMSConfig.get_all_schedules()
        except AMSConfigException as e:
            self.AMSLogger.debug(str(e))
        self.num_schedules = len(self.all_schedules_obj)
        self.AMSZabbix = AMSZabbix(self.AMSLogger, self.AMSConfig,
                                   username=self.username, password=self.password)
        self.AMSZabbix.retry_limit = -1
        self.lld_zabbix_key = lld_zabbix_key

    def generate_lld_dict(self):
        # adding a call to create the default, ad-hoc schedule for anything that doesn't match in the config.
        self._add_adhoc_schedule_to_json()

        if self.num_schedules < 1:
            return True

        for project_schedule_name, schedule_data_dict in self.all_schedules_obj.iteritems():  # type: str, dict
            tmp_dict = dict()
            tmp_dict['{#SCHEDULE}'] = schedule_data_dict['project_name'] + '::' + schedule_data_dict['schedule_name']
            self.lld_dict['data'].append(tmp_dict)

        return True

    def _add_adhoc_schedule_to_json(self):
        tmp_dict = dict()
        tmp_dict['{#SCHEDULE}'] = self.AMSDefaults.default_adhoc_schedule_key
        self.lld_dict['data'].append(tmp_dict)

    def is_authenticated(self):
        return self.AMSZabbix.is_authenticated()

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