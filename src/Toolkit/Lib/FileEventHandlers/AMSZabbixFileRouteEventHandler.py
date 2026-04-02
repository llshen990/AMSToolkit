import json
import sys
import collections
import os
from datetime import datetime

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.FileEventHandlers import AbstractAMSFileRouteEventHandler
from Toolkit.Lib.EventHandlers import AbstractStateEventHandler
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Config import AMSConfig
from Toolkit.Views import CommandLineConfigView
from Toolkit.Models.AMSFileRouteLLD import AMSFileRouteLLD
from Toolkit.Exceptions import AMSZabbixException, AMSConfigException



class AMSZabbixFileRouteEventHandler(AbstractAMSFileRouteEventHandler,AbstractStateEventHandler):


    def __init__(self, logger, config, route_name):
        """
        :param logger: The Logger instance
        :type logger: AMSLogger
        :param config: The Config instance
        :type config: AMSConfig
        :param route_name: The route name
        :type route_name: str
        """
        AbstractAMSFileRouteEventHandler.__init__(self)
        AbstractStateEventHandler.__init__(self)

        self.AMSZabbix = AMSZabbix(logger, config)
        # For backwards compatibility, unless there is a configured zabbix_timeout in the config, use 2 seconds as the default
        if not config or 'zabbix_retry_timeout' not in config.raw_config:
            self.AMSZabbix.retry_timeout = 2
        self.route_name = route_name
        self.start_time = None
        self.end_time = None
        self.start_time_dt = None
        self.ams_config = config
        self.ams_defaults = AMSDefaults()

        try:
            self.route = self.ams_config.get_file_route_by_name(self.route_name)
        except AMSConfigException as e:
            self.AMSLogger.error('Failed to retrieve AMSFileRoute object from route name : {} - {}'.format((self.route_name, str(e))))

        self.route_key = self.route.get_route_zabbix_key()

    def __get_zabbix_key(self, key):
        return str(key) + "[{0}]".format(self.route_key)

    def _do_lld(self):
        try:
            ams_file_route_lld = AMSFileRouteLLD(self.ams_config, self.ams_defaults.zabbix_file_route_lld_key,single_route=self.route_name)
            ams_file_route_lld.generate_lld_dict()
            self.AMSLogger.info('Making LLD request with JSON: {}'.format(json.dumps(ams_file_route_lld.lld_dict, indent=2)))
            ams_file_route_lld.invoke_zabbix_lld()
        except AMSZabbixException as e:
            self.AMSLogger.error('LLD failed to run for file route: {} - {}'.format(self.route_name, str(e)))

    def _before_start(self):
        # batch.error=0
        # No point in checking the return code if this succeeds it doesn't mean that LLD succeeds, just means that it was sent
        self._do_lld()

        # Check the error code of the zabbix send for the batch.error=0 to see if LLD is successfull
        if not self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_error), AMSZabbixFileRouteEventHandler.batch_initial_value):
            self.AMSLogger.warning('File Route {} may not be enabled in Zabbix!'.format(self.route_key))
            return False

        self.AMSLogger.debug('LLD completed successfully for route: {}'.format(self.route_name))

        # automation.name=route_name
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.automation_name), self.route_key)

        # automation.type=File Route
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.automation_type), 'File Route')

        # batch.delay=0
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_delay), AMSZabbixFileRouteEventHandler.batch_initial_value)

        # batch.config_raw -> raw JSON config
        config = collections.OrderedDict()

        try:
            config['environments'] = self.ams_config.raw_config['environments']
            if self.ams_config.raw_config['file_routes']:
                config['file_routes']= self.ams_config.raw_config['file_routes']
                if config['file_routes']:
                    for route in config['file_routes']:
                        if route != self.route_name:
                            del config['file_routes'][route]
        except Exception as e:
            self.AMSLogger.warning('Problem finding config for route_key {}: e'.format(self.route_key, e))

        try:
            value = json.JSONEncoder().encode(config)
        except:
            self.AMSLogger.warning('Problem json encoding value {}:'.format(config))
            value = ''

        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_config_raw), value)
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
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_info), "File route {} is checking dependency: {}.".format(self.route_key, info))

    def _on_start(self):
        self.start_time_dt = datetime.now()
        # batch.running=1
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_running), AMSZabbixFileRouteEventHandler.batch_start_value)
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_info), "File route {} has started.".format(self.route_key))

    def _on_error(self):
        # batch.error = 1
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_error), AMSZabbixFileRouteEventHandler.batch_error_value)
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_info), "File route {} has an error or has been killed.".format(self.route_key))

    def _on_finish(self):
        if self.start_time_dt is not None:
            self.end_time = (datetime.now() - self.start_time_dt).seconds
            self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_runtime), str(self.end_time))
        else:
            self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_runtime), '0')

        # batch.running=0
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_running), AMSZabbixFileRouteEventHandler.batch_initial_value)

    def _on_info(self, info):
        # update batch.batch_info with the info
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_info), "File route {} {}".format(self.route_key, info))

    def _after_finish(self):
        # update batch.message saying batch is complete
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_info), "File route {} has completed.".format(self.route_key))

    def _on_batch_delay(self):
        # batch.delay =1
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_delay), AMSZabbixFileRouteEventHandler.batch_delay_value)
        self.AMSZabbix.call_zabbix_sender(self.__get_zabbix_key(AMSZabbixFileRouteEventHandler.batch_info), "File route {} has a batch delay for failing one or more dependencies.".format(self.route_key))

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

    def __del__(self):
        # @todo: write bundle cache to disk
        pass