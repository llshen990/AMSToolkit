import sys
import logging
import abc
import os
import importlib

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

class AbstractAMSFileRouteEventHandler(object):
    __metaclass__ = abc.ABCMeta

    @staticmethod
    def create_handler(logger, ams_config, schedule_name):
        try:
            module = importlib.import_module(
                'Toolkit.Lib.FileEventHandlers.' + ams_config.ams_event_handler + 'FileRouteEventHandler')
            clazz = getattr(module, ams_config.ams_event_handler + 'FileRouteEventHandler')
            return clazz(logger, ams_config, schedule_name)
        except Exception as e:
            return None

    def __init__(self):
        self.AMSLogger = logging.getLogger('AMS')
        pass

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

    def __del__(self):
        # @todo: write bundle cache to disk
        pass