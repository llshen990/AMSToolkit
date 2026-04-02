import json
import sys

import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.FileEventHandlers import AbstractAMSFileRouteEventHandler
from Toolkit.Lib.EventHandlers import AbstractStateEventHandler
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Config import AMSConfig
from Toolkit.Views import CommandLineConfigView


class AMSEmailFileRouteEventHandler(AbstractAMSFileRouteEventHandler,AbstractStateEventHandler):

    def __init__(self, logger, config, schedule_name=None):
        """
        :param logger: The Logger instance
        :type logger: AMSLogger
        :param config: The Config instance
        :type config: AMSConfig
        :param schedule_name: The schedule name
        :type schedule_name: str
        """
        AbstractAMSFileRouteEventHandler.__init__(self)
        self.schedule_name = schedule_name
        self.ams_config = config
        self.ams_defaults = AMSDefaults()

    def _before_start(self):
        pass

    def _generate_human_readable_config(self, config_object=None):
        generate_human_readable_config = CommandLineConfigView()
        generate_human_readable_config.display_only = True
        if config_object is None:
            config_object = self.ams_config

        tmp_config_object_copy = config_object
        generate_human_readable_config.generate_command_line_config_prompts(tmp_config_object_copy)
        return generate_human_readable_config.display_only_str

    def _on_start(self):
        pass

    def _on_dependency(self, info):
        pass

    def _on_error(self):
        pass

    def _on_finish(self):
        pass

    def _on_info(self, info):
        pass

    def _after_finish(self):
        pass

    def _on_long_running(self):
        pass

    def _on_short_running(self):
        pass

    def _on_batch_delay(self):
        pass

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

    def __del__(self):
        # @todo: write bundle cache to disk
        pass
