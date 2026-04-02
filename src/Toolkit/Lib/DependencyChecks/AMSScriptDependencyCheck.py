import subprocess
import sys

import os

from Toolkit.Lib.AMSScriptReturnCode import AMSScriptReturnCode

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.DependencyChecks import AbstractAMSDependencyCheck

class AMSScriptDependencyCheck(AbstractAMSDependencyCheck):
    """
    This class will execute s script on the commandline and return the results.
    """

    # @todo: will ensure that the script returns successfully (exit code 0) or a -1 (sleep and check again after x seconds per internal default config y times per internal default config)

    def __init__(self, ams_config, ams_dependency_checker):
        """
        :param ams_config:
        :type: AMSConfig
        :param ams_dependency_checker:
        :type: AMSDependencyChecker
        """
        AbstractAMSDependencyCheck.__init__(self, ams_config, ams_dependency_checker)
        self.args = self.AMSDependencyChecker.dependency.strip().split()

    def _check_dependency(self):
        """
        This method executes the script and returns the results in a AMSScriptReturnCode object
        :return: AMSReturnCode:
        """

        msg = "Dependency check " + self.AMSDependencyChecker.dependency
        try:
            p = subprocess.Popen(self.args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
            # start the future
            self.AMSLogger.info("Exec'd pid=" + str(p.pid) + " args=" + " ".join(self.args))
            std_out, std_err = p.communicate()

            # print when finished
            self.AMSLogger.info("Finished pid=" + str(p.pid) + "\n" + std_out.strip() + "\nrc=" + str(p.returncode))

            msg = msg + "\n" + std_out
            return AMSScriptReturnCode(p.pid, p.returncode, msg, std_err, self.AMSDependencyChecker.dependency.strip())
        except Exception as e:
            # Don't raise an exception but be sure to return a failed return code with information
            self.AMSLogger.error('Failed script dependency due to exception: %s' % str(e))
            return AMSScriptReturnCode(0, 1, msg, str(e), self.AMSDependencyChecker.dependency.strip())

    def instructions_for_verification(self):
        ret_str = 'The below command should return with a zero exit code: {}{}'.format(os.linesep, ' '.join(self.args))
        return ret_str
