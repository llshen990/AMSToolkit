import glob
import sys

import os

from Toolkit.Lib.AMSReturnCode import AMSReturnCode

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.DependencyChecks import AbstractAMSDependencyCheck

class AMSIncomingFileMultiDependencyCheck(AbstractAMSDependencyCheck):
    """
    Will ensure one or more file(s) are present of a given file pattern.
    """

    def __init__(self, ams_config, ams_dependency_checker):  #
        """
        :param ams_config:
        :type: AMSConfig
        :param ams_dependency_checker:
        :type: AMSDependencyChecker
        """
        AbstractAMSDependencyCheck.__init__(self, ams_config, ams_dependency_checker)
        self.directory = self.AMSConfig.get_incoming_directory_by_schedule_name(self.AMSDependencyChecker.schedule_name)
        self.found_dependency = []
        self.failed_dependency = []

    def _check_dependency(self):
        """
        This checks the dependency and returns true if it is successful and false otherwise.
        :return:
        :type: bool
        """
        # Reset the found and failed dependencies each time
        #  Otherwise the instructions_for_verification will have failure results from every iteration
        self.found_dependency = []
        self.failed_dependency = []
        res = True
        msg = "Dependency check "
        try:
            for dependencies in self.AMSDependencyChecker.dependency.split(","):
                file_list = glob.glob(os.path.join(self.directory, dependencies.strip()))
                if len(file_list) >= 1:
                    msg = msg + ": Check for " + dependencies + " is successful. "
                    self.found_dependency.append(file_list)
                else:
                    res = False
                    self.failed_dependency.append(dependencies)
                    msg = msg + ": Check for " + dependencies + " is unsuccessful. "
            return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)
        except Exception as e:
            res = False
            msg = msg + ": " + e.message
            return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)

    def instructions_for_verification(self):
        ret_str = 'There should be one or more file(s) matching the below commands:%s' % os.linesep
        for dependency in self.failed_dependency:
            ret_str += 'ls -la %s' % os.path.join(self.directory, dependency.strip()) + os.linesep

        if self.found_dependency:
            ret_str += '{}Note: The following files were found:{}'.format(os.linesep, os.linesep)
            for dependency in self.found_dependency:
                if dependency:
                    for f in dependency:
                        ret_str += os.path.join(self.directory, f.strip()) + os.linesep

        else:
                ret_str += '{}Note: No files were found!{}'.format(os.linesep, os.linesep)

        return ret_str

    def commandline_output(self):
        ret_str = 'There should be one or more file(s) matching the below:%s' % os.linesep
        for dependency in self.failed_dependency:
            ret_str += os.path.join(self.directory, dependency.strip()) + os.linesep

        if self.found_dependency:
            ret_str += '{}Note: The following files were found:{}'.format(os.linesep, os.linesep)
            for dependency in self.found_dependency:
                if dependency:
                    for f in dependency:
                        ret_str += os.path.join(self.directory, f.strip()) + os.linesep

        else:
                ret_str += '{}Note: No files were found!{}'.format(os.linesep, os.linesep)

        return ret_str
