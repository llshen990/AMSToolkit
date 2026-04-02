import sys

import os

from lib.Validators import FileExistsValidator
from Toolkit.Lib import AMSReturnCode
from Toolkit.Lib.CompleteHandlers import AbstractCompleteHandler
from Toolkit.Lib.Helpers import AMSFile

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)


class AMSClearSignalCompleteHandler(AbstractCompleteHandler):
    """
    This class will execute a command on the commandline and return the results.
    """

    def __init__(self, ams_config, ams_complete_handler):
        """
        :param ams_config:
        :type: AMSConfig
        :param ams_complete_handler:
        :type: AMSCompleteHandler
        """
        AbstractCompleteHandler.__init__(self, ams_config, ams_complete_handler)
        self.fev = FileExistsValidator()
        self.directory = None

    def _run_complete_handler(self, schedule, is_success):
        """
        This method checks the specified file exists and executes the remove command. Returns an AMSReturnCode object.
        :return: AMSReturnCode:
        """
        try:
            # Append sig_dir from schedule if a relative path is used
            if self.AMSCompleteHandler.complete_handler.strip()[0] == os.sep:
                self.sig_file = self.AMSCompleteHandler.complete_handler.strip()
            else:
                self.sig_file = os.path.join(schedule.signal_dir, self.AMSCompleteHandler.complete_handler)

            self.directory = os.path.dirname(self.sig_file)

            # Check read access to existing file
            if self.fev.validate(self.sig_file):
                try:
                    self.AMSLogger.info(
                        "Validated read access to existing file: %s" % str(self.sig_file))
                    AMSFile.clear(self.sig_file)
                    if not self.fev.validate(self.sig_file):
                        res = True
                        msg = "Successfully Cleared Signal: %s" % str(self.sig_file)
                    else:
                        raise Exception
                except Exception as E:
                    res = False
                    msg = "Failed to Clear Signal: %s" % str(E)
                return AMSReturnCode(self.sig_file, res, msg)

            else:
                res = False
                msg = "Signal does not exist: %s" % str(self.sig_file)
                return AMSReturnCode(self.sig_file, res, msg)

        except Exception as e:
            self.AMSLogger.error('Failed to Clear Signal due to exception: %s' % str(e))
            raise

    def instructions_for_verification(self):
        ret_str = 'Verify the following directory exists and can be read and written to: %s' % str(self.directory) + os.linesep
        ret_str += 'And that directory contains the following filename: %s' % os.path.basename(self.AMSCompleteHandler.complete_handler)
        return ret_str
