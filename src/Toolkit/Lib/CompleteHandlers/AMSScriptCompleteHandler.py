import subprocess
import sys
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from Toolkit.Lib import AMSScriptReturnCode, AMSReturnCode
from Toolkit.Lib.CompleteHandlers import AbstractCompleteHandler


class AMSScriptCompleteHandler(AbstractCompleteHandler):
    """
    This class will execute s script on the commandline and return the results.
    """

    # @todo: will ensure that the script returns successfully (exit code 0) or a -1 (sleep and check again after x seconds per internal default config y times per internal default config)

    def __init__(self, ams_config, ams_complete_handler):
        """
        :param ams_config:
        :type: AMSConfig
        :param ams_complete_handler:
        :type: AMSCompleteHandler
        """
        AbstractCompleteHandler.__init__(self, ams_config, ams_complete_handler)

        self.script = self.AMSCompleteHandler.complete_handler.strip()
        # if a service_parm has been added, then use it -- otherwise check for the old skool
        if len(self.AMSCompleteHandler.service_params) > 0:
            self.args = [self.script]
            for arg in self.AMSCompleteHandler.service_params:
                arg = str(arg).split()[0]
                if arg:
                    self.args.append(arg)
        else:
            self.args = self.script.split()

    def _run_complete_handler(self, schedule, is_success):
        """
        This method executes the script and returns the results in a AMSScriptReturnCode object
        :return: AMSScriptReturnCode:
        """
        if not FileExistsValidator().is_exe(self.script):
            return AMSReturnCode(self.AMSCompleteHandler.complete_handler, False, 'Script %s does not exist or is not executable' % self.script)

        msg = "Complete Handler " + self.AMSCompleteHandler.complete_handler
        try:
            p = subprocess.Popen(self.args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
            # start the future
            self.AMSLogger.info("Exec'd pid=" + str(p.pid) + " args=" + " ".join(self.args))
            std_out, std_err = p.communicate()

            # print when finished
            self.AMSLogger.info("Finished pid=" + str(p.pid) + "\n" + std_out.strip() + "\nrc=" + str(p.returncode))

            msg = msg + "\n" + std_out
            return AMSScriptReturnCode(p.pid, p.returncode, msg, std_err, self.script)
        except Exception as e:
            self.AMSLogger.error('Failed script complete handler ({}) due to exception: {}'.format(self.script, str(e)))
            raise

    def instructions_for_verification(self):
        ret_str = 'The below command should return with a zero exit code: ' + os.linesep
        ret_str += '%s' % self.script
        return ret_str