import sys
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.ScheduleEventHandlers import AbstractAMSScheduleEventHandler
from Toolkit.Lib.EventHandlers import AbstractStateEventHandler
from Toolkit.Config import AMSConfig


class AMSLoggerScheduleEventHandler(AbstractAMSScheduleEventHandler,AbstractStateEventHandler):

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

    def _before_start(self):
        pass

    def _on_start(self):
        pass

    def _on_dependency(self, info):
        pass

    def _on_info(self, info):
        pass

    def _on_error(self):
        pass

    def _on_finish(self):
        pass

    def _after_finish(self):
        pass

    def _on_long_running(self):
        pass

    def _on_short_running(self):
        pass

    def _on_batch_delay(self):
        pass