import glob
import sys

import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.DependencyChecks import AbstractAMSDependencyCheck
from Toolkit.Lib.AMSReturnCode import AMSReturnCode

class AMSIncomingFileSingleDependencyCheck(AbstractAMSDependencyCheck):
    """
    Will implement functionality to ensure only one file of the given file pattern is present.
    """

    def __init__(self, ams_config, ams_dependency_checker):
        """
        :param ams_config:
        :type: AMSConfig
        :param ams_dependency_checker:
        :type: AMSDependencyChecker
        """
        AbstractAMSDependencyCheck.__init__(self, ams_config, ams_dependency_checker)
        self.directory = self.AMSConfig.get_incoming_directory_by_schedule_name(self.AMSDependencyChecker.schedule_name)
        self.failed_dependency = ""
    #    self._regex_validator = RegExValidator(True)

    def _check_dependency(self):
        """
        This checks the dependency and returns true if it is successful and false otherwise.
        :return AMSReturnCode:
        :type: bool
        """
        res = True
        msg = "Dependency check "
        try:
            for dependencies in self.AMSDependencyChecker.dependency.split(","):
                file_list = glob.glob(os.path.join(self.directory, dependencies.strip()))
                if len(file_list) == 1:
                    msg = msg + ": Check for " + dependencies + " is successful. "
                else:
                    res = False
                    self.failed_dependency = self.failed_dependency + dependencies
                    msg = msg + ": Check for " + dependencies + " is unsuccessful. "
            return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)
        except Exception as e:
            res = False
            msg = msg + ": " + e.message
            return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)

    def instructions_for_verification(self):
        ret_str = 'There should only be one file matching the below command:%s' % os.linesep
        ret_str += 'ls -la %s' % (os.path.join(self.directory, self.failed_dependency.strip()))
        return ret_str

    def commandline_output(self):
        ret_str = 'There should only be one file matching the below:%s' % os.linesep
        ret_str += os.path.join(self.directory, self.failed_dependency.strip())
        return ret_str
