import sys
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.DependencyChecks import AbstractAMSDependencyCheck
from Toolkit.Lib.AMSReturnCode import AMSReturnCode
from Toolkit.Lib.Helpers.ProcCheck import ProcCheck

class AMSScheduleNotRunningDependencyCheck(AbstractAMSDependencyCheck):
    """
    This class checks a port of the host is accepting connections.
    """

    def __init__(self, ams_config, ams_dependency_checker):
        """
        :param ams_config:
        :type:  AMSConfig
        :param ams_dependency_checker:
        :type: AMSDependencyChecker
        """
        AbstractAMSDependencyCheck.__init__(self, ams_config, ams_dependency_checker)

    def _check_dependency(self):
        """
        This checks the dependency and returns true if it is successful and false otherwise.
        :return:
        :type: bool
        """
        res = False
        msg = "Dependency check " + self.AMSDependencyChecker.dependency
        try:
            lock_dir = self.AMSConfig.get_signal_directory_by_schedule_name(self.AMSDependencyChecker.dependency)
            proc_check = ProcCheck(controller_name='ams_schedule_launcher', context=self.AMSDependencyChecker.dependency, lock_dir=lock_dir)
            self.lock_file_name = proc_check.lock_file_name
            result = proc_check.lock_file_present()
            if not result:
                self.AMSLogger.info("Schedule " + self.AMSDependencyChecker.dependency + " is not running")
                res = True
                msg = msg + "Schedule " + self.AMSDependencyChecker.dependency + " is not running"
            else:
                self.AMSLogger.info("Schedule " + self.AMSDependencyChecker.dependency + " is running")
                msg = msg + "Schedule " + self.AMSDependencyChecker.dependency + " is running"
                res = False
            return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)
        except Exception as e:
            msg = msg + ": " + e.message
            return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)

    def instructions_for_verification(self):
        ret_str = self.commandline_output()
        ret_str += '{}ls -la {}'.format(os.linesep, self.lock_file_name)
        return ret_str

    def commandline_output(self):
        ret_str = 'The following schedule is still running {}.{}{}'.format(self.AMSDependencyChecker.dependency, os.linesep, os.linesep)
        ret_str += 'Please inspect all running processes and examine the following lockfile:{}{}{}'.format(os.linesep, self.lock_file_name, os.linesep)
        return ret_str