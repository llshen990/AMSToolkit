import sys
import logging
import abc
import os
import importlib

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

class AbstractAMSScheduleEventHandler(object):
    __metaclass__ = abc.ABCMeta

    @staticmethod
    def create_handler(logger, ams_config, schedule_name):
        try:
            module = importlib.import_module('Toolkit.Lib.ScheduleEventHandlers.' + ams_config.ams_event_handler + 'ScheduleEventHandler')
            clazz = getattr(module, ams_config.ams_event_handler + 'ScheduleEventHandler')
            return clazz(logger, ams_config, schedule_name)
        except Exception as e:
            return None

    def __init__(self):
        self.AMSLogger = logging.getLogger('AMS')
        self.schedule_name = None
        pass

    def set_schedule(self, schedule_name):
        self.schedule_name = schedule_name

    @abc.abstractmethod
    def _on_long_running(self):
        pass

    @abc.abstractmethod
    def _on_short_running(self):
        pass


    def on_long_running(self):
        # @todo: implement any logic that applies to all ScheduleEventHandlers.  Raise AMSScheduleEventHandlerException on errors.
        self._on_long_running()

    def on_short_running(self):
        # @todo: implement any logic that applies to all ScheduleEventHandlers.  Raise AMSScheduleEventHandlerException on errors.
        self._on_short_running()


    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

    def __del__(self):
        # @todo: write bundle cache to disk
        pass