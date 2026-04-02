import json
import sys
import collections
import os
from datetime import datetime

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.ScheduleEventHandlers import AbstractAMSScheduleEventHandler
from Toolkit.Lib.EventHandlers import AbstractStateEventHandler
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Config import AMSConfig
from Toolkit.Views import CommandLineConfigView
from Toolkit.Exceptions import AMSScheduleException
from Toolkit.Models import AMSScheduleLLD
from Toolkit.Exceptions import AMSZabbixException

class AMSZabbixScheduleEventHandler(AbstractAMSScheduleEventHandler,AbstractStateEventHandler):

    batch_long_running = 'batch.longrunning'
    batch_short_running = 'batch.shortrunning'
    batch_long_running_value = '1'
    batch_short_running_value = '1'


    def __init__(self, logger, config, schedule_name=None):
        """
        :param logger: The Logger instance
        :type logger: AMSLogger
        :param config: The Config instance
        :type config: AMSConfig
        :param schedule_name: The schedule name
        :type schedule_name: str
        """
        AbstractAMSScheduleEventHandler.__init__(self)
        AbstractStateEventHandler.__init__(self)
        self.AMSZabbix = AMSZabbix(logger, config)
        self.schedule_name = schedule_name
        self.start_time = None
        self.end_time = None
        self.start_time_dt = None
        self.ams_config = config
        self.ams_defaults = AMSDefaults()
        self.set_schedule(schedule_name)
        self.did_lld = False

    def set_schedule(self, schedule_name):
        # get the schedule if named
        if schedule_name is None:
            self.schedule_key = AMSDefaults().default_adhoc_schedule_key
            self.schedule = self.ams_config.get_adhoc_schedule_object()
        else:
            try:
                self.schedule = self.ams_config.get_schedule_by_name(schedule_name)
            except AMSScheduleException:
                self.schedule = self.ams_config.get_adhoc_schedule_object()
            self.schedule_key = self.schedule.get_schedule_zabbix_key()

        self.schedule_name = self.schedule.schedule_name

    def __get_zabbix_key(self, key):
        return str(key) + "[{0}]".format(self.schedule_key)

    def _do_lld(self):
        try:
            if not self.did_lld:
                ams_schedule_lld = AMSScheduleLLD(self.ams_config, self.ams_defaults.zabbix_batch_monitoring_lld_key, single_schedule=self.schedule_name)
                ams_schedule_lld.generate_lld_dict()
                self.AMSLogger.info('Making LLD request with JSON: %s' % json.dumps(ams_schedule_lld.lld_dict, indent=2))
                ams_schedule_lld.invoke_zabbix_lld()
                self.did_lld = True
        except AMSZabbixException as e:
            self.AMSLogger.error('LLD failed to run for schedule: %s - %s' % (self.schedule_name, str(e)))

    def _before_start(self):
        # batch.error=0
        # No point in checking the return code if this succeeds it doesn't mean that LLD succeeds, just means that it was sent
        self._do_lld()

        # Check the error code of the zabbix send for the batch.error=0 to see if LLD is successfull
        if not self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_error), AMSZabbixScheduleEventHandler.batch_initial_value):
            self.AMSLogger.warning('Schedule {} may not be enabled in Zabbix!'.format(self.schedule_key))
            return False

        self.AMSLogger.debug('LLD completed successfully for schedule: %s' % self.schedule_name)

        # automation.name=schedule_name
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.automation_name), self.schedule_key)

        # automation.type=Schedule
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.automation_type), 'Schedule')

        # batch.delay=0
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_delay), AMSZabbixScheduleEventHandler.batch_initial_value)
        # batch.longrunning=0
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_long_running), AMSZabbixScheduleEventHandler.batch_initial_value)

        # batch.config_raw -> raw JSON config
        config = collections.OrderedDict()
        try:
            # copy the environments and projects to a new config dictionary
            config['environments'] = self.ams_config.raw_config['environments']
            config['projects'] = collections.OrderedDict()
            # project name isn't stored anywhere, so let's just get lucky here?
            # we could get the schedule with self.ams_config.get_schedule_by_name() and convert that to JSON but this will work as well
            project_name = self.schedule_key.split('::')[0]
            # then, copy the current project
            if self.ams_config.raw_config['projects'] and self.ams_config.raw_config['projects'][project_name]:
                config['projects'][project_name] = self.ams_config.raw_config['projects'][project_name]
                #  and ensure only the current schedule remains in the config
                if config['projects'][project_name]['schedules']:
                    for schedule in config['projects'][project_name]['schedules']:
                        if schedule != self.schedule_name:
                            del config['projects'][project_name]['schedules'][schedule]
        except Exception as e:
            self.AMSLogger.warning('Problem finding config for schedule_key {}: e'.format(self.schedule_key, e))

        try:
            value = json.JSONEncoder().encode(config)
        except:
            self.AMSLogger.warning('Problem json encoding value {}:'.format(config))
            value = ''

        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_config_raw), value)
        return True

    def _generate_human_readable_config(self, config_object=None):
        generate_human_readable_config = CommandLineConfigView()
        generate_human_readable_config.display_only = True
        if config_object is None:
            config_object = self.ams_config

        tmp_config_object_copy = config_object
        generate_human_readable_config.generate_command_line_config_prompts(tmp_config_object_copy)
        return generate_human_readable_config.display_only_str

    def _on_dependency(self, info):
        self._do_lld()
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_info), "Schedule {} is checking dependency {}".format(self.schedule_key, info))

    def _on_info(self, info):
        # update batch.batch_info with the info
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_info), "Schedule {} {}".format(self.schedule_key, info))

    def _on_start(self):
        self.start_time_dt = datetime.now()
        # batch.running=1
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_running), AMSZabbixScheduleEventHandler.batch_start_value)
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_info), "Schedule %s has started." % self.schedule_key)

    def _on_error(self):
        # batch.error = 1
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_error), AMSZabbixScheduleEventHandler.batch_error_value)
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_info), "Schedule %s has an error or has been killed." % self.schedule_key)

    def _on_finish(self):
        if self.start_time_dt is not None:
            self.end_time = (datetime.now() - self.start_time_dt).seconds
            self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_runtime), str(self.end_time))
        else:
            self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_runtime), '0')

        # batch.running=0
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_running), AMSZabbixScheduleEventHandler.batch_initial_value)

    def _after_finish(self):
        # update batch.message saying batch is complete
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_info), "Schedule %s has completed." % self.schedule_key)
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_long_running), AMSZabbixScheduleEventHandler.batch_initial_value)

    def _on_long_running(self):
        # batch.longrunning = 1
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_info), "Schedule %s is running long." % self.schedule_key)
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_long_running), AMSZabbixScheduleEventHandler.batch_long_running_value)

    def _on_short_running(self):
        # batch.shortrunning = 1
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_info), "Schedule %s is running short." % self.schedule_key)
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_short_running), AMSZabbixScheduleEventHandler.batch_short_running_value)

    def _on_batch_delay(self):
        # batch.delay =1
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_delay), AMSZabbixScheduleEventHandler.batch_delay_value)
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixScheduleEventHandler.batch_info), "Schedule %s has a batch delay for failing one or more dependencies." % self.schedule_key)

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

    def __del__(self):
        # @todo: write bundle cache to disk
        pass