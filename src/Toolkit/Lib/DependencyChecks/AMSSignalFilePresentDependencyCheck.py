import glob
import sys

import os

from Toolkit.Exceptions import AMSConfigException

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.DependencyChecks import AbstractAMSDependencyCheck
from Toolkit.Lib.AMSReturnCode import AMSReturnCode

class AMSSignalFilePresentDependencyCheck(AbstractAMSDependencyCheck):
    """
    Will implement functionality to check the the signal file is not present
    """

    def __init__(self, ams_config, ams_dependency_checker):
        """
        :param ams_config:
        :type: AMSConfig
        :param ams_dependency_checker:
        :type: AMSDependencyChecker
        """
        AbstractAMSDependencyCheck.__init__(self, ams_config, ams_dependency_checker)

        try:
            self.sig_dir = self.AMSConfig.get_signal_directory_by_schedule_name(self.AMSDependencyChecker.schedule_name)
        except AMSConfigException as e:
            self.sig_dir = os.path.dirname(self.AMSDependencyChecker.dependency)

        self.sig_file = None

        if '' == self.sig_dir:
            self.sig_dir = os.getcwd()

    def _check_dependency(self):
        """
        This checks the dependency and returns true if it is successful and false otherwise.
        :return AMSReturnCode:
        :type: AMSReturnCode
        """
        res = False
        msg = "Dependency check " + self.AMSDependencyChecker.dependency
        try:
            if self.AMSDependencyChecker.dependency.strip()[0] == '/':
                self.sig_file = self.AMSDependencyChecker.dependency.strip()
            else:
                self.sig_file = os.path.join(self.sig_dir, self.AMSDependencyChecker.dependency)

            self.AMSLogger.info('Checking for signal file in {}'.format(self.sig_dir))

            file_list = glob.glob(self.sig_file)
            if len(file_list) > 0:
                res = True
                msg = msg + " is successful"
            else:
                msg = msg + " is unsuccessful"
            return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)
        except Exception as e:
            msg = msg + ": " + e.message
            return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)

    def instructions_for_verification(self):
        ret_str = 'There should be a file matching the below command:%s' % os.linesep
        ret_str += 'ls -la %s' % (os.path.join(self.sig_dir, self.AMSDependencyChecker.dependency))
        return ret_str

    def commandline_output(self):
        return 'The below signal file should be present but it is absent:{}{}'.format(os.linesep, os.path.join(self.sig_dir, self.AMSDependencyChecker.dependency))