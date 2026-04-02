import sys
import abc
import os
import logging

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.AMSReturnCode import AMSReturnCode
from Toolkit.Config import AMSConfig, AMSCompleteHandler

class AbstractCompleteHandler(object):
    """
    Base class for success/error handler check classes
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, ams_config, ams_complete_handler):
        self.AMSLogger = logging.getLogger('AMS')

        self.AMSConfig = ams_config # type: AMSConfig
        self.AMSCompleteHandler = ams_complete_handler # type: AMSCompleteHandler

    @abc.abstractmethod
    def _run_complete_handler(self, schedule, is_success):
        pass

    @abc.abstractmethod
    def instructions_for_verification(self):
        """
        This method will be implemented by the derived classes to build verification instructions for how to manually validate the complete handler that failed.
        :return:
        """
        pass

    def commandline_output(self):
        """
        This method will be implemented by the derived classes to build verification instructions for how to manually validate the complete handler that failed.
        :return:
        """
        return self.instructions_for_verification()

    def evaluate_complete_handler(self, schedule, is_success):
        """
        This method will be implemented by the derived classes to design any logic that applies to all complete handler(s).
        :return: AMSReturnCode
        """
        return self._run_complete_handler(schedule, is_success) # type: AMSReturnCode