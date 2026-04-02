import sys
import time
import logging
import abc
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.AMSReturnCode import AMSReturnCode
from Toolkit.Config import AMSConfig, AMSDependencyChecker


class AbstractAMSDependencyCheck(object):
    """
    Base class for dependency check classes
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, ams_config, ams_dependency_checker):
        """
        :param ams_config:
        :type: AMSConfig
        :param ams_dependency_checker:
        :type: AMSDependencyChecker
        """

        self.AMSLogger = logging.getLogger('AMS')

        self.AMSConfig = ams_config  # type: AMSConfig
        self.AMSDependencyChecker = ams_dependency_checker  # type: AMSDependencyChecker
        if self.AMSDependencyChecker.max_attempts:
            self.max_attempts = self.AMSDependencyChecker.max_attempts  # dependency['max_attempts'] # type: int
        else:
            self.max_attempts = 1
        if self.AMSDependencyChecker.attempt_interval:
            self.attempt_interval = self.AMSDependencyChecker.attempt_interval  # type: int
        else:
            self.attempt_interval = 0

    @abc.abstractmethod
    def _check_dependency(self):
        """
        This method will be implemented by the derived classes to check the dependency.
        :return:
        """
        pass

    @abc.abstractmethod
    def instructions_for_verification(self):
        """
        This method will be implemented by the derived classes to build verification instructions for how to validate the dependency failed manually.
        :return:
        """
        pass

    def commandline_output(self):
        """
        This method will be implemented by the derived classes to build verification instructions for how to validate the dependency failed manually.
        :return:
        """
        return self.instructions_for_verification()

    def evaluate_dependency(self):
        """
        implement any logic that applies to all DependencyChecks.  Raise AMSDependencyCheckException on errors.
        :return: AMSReturnCode
        """
        res = None  # type: AMSReturnCode
        iterations = 0
        while iterations < self.max_attempts:
            printable_iterations = iterations + 1
            self.AMSLogger.info("[%s] Starting iteration #%s.  checking dependency %s on dependency %s." % (self.AMSDependencyChecker.type, printable_iterations, self.AMSDependencyChecker.dependency_check_name, self.AMSDependencyChecker.dependency))
            res = self._check_dependency()
            if res.job_success:
                self.AMSLogger.info('[%s][SUCCESS] Passed dependency %s.' % (self.AMSDependencyChecker.type, self.attempt_interval))
                return res
            else:
                self.AMSLogger.critical('[%s][FAILED] Max attempts is set to %s.  current attempt is %s.  Sleeping %s seconds.' % (self.AMSDependencyChecker.type, self.max_attempts, printable_iterations, self.attempt_interval))
                iterations += 1
                if iterations == self.max_attempts:
                    return res
                time.sleep(self.attempt_interval)
        else:
            return res