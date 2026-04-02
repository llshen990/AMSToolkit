import sys

import os

from lib.Validators import FileExistsValidator
from Toolkit.Lib import AMSReturnCode
from Toolkit.Lib.CompleteHandlers import AbstractCompleteHandler
from Toolkit.Lib.Helpers import AMSTouch

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)


class AMSTouchFileCompleteHandler(AbstractCompleteHandler):
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
        This method checks the specified directory and executes the touch command. Returns an AMSReturnCode object.
        :return: AMSReturnCode:
        """
        try:
            # Append sig_dir from schedule if a relative path is used
            if self.AMSCompleteHandler.complete_handler.strip()[0] == '/':
                self.sig_file = self.AMSCompleteHandler.complete_handler.strip()
            else:
                self.sig_file = os.path.join(schedule.signal_dir, self.AMSCompleteHandler.complete_handler)

            self.directory = os.path.dirname(self.sig_file)

            # Check read and write access to existing directory
            if self.fev.directory_exists(self.directory) and self.fev.directory_writeable(self.directory):
                try:
                    self.AMSLogger.info(
                        "Validated read and write access to existing directory: %s" % str(self.directory))
                    AMSTouch.touch(self.sig_file)
                    if self.fev.validate(self.sig_file):
                        res = True
                        msg = "Successfully Touched %s" % str(self.sig_file)
                    else:
                        raise Exception
                except Exception as E:
                    res = False
                    msg = "Failed to Create Touch File: %s" % str(E)

            else:
                res = False
                if not self.fev.directory_exists(self.directory):
                    msg = "Directory does not exist: "
                elif not self.fev.directory_readable(self.directory):
                    msg = "Directory is not readable: "
                elif not self.fev.directory_writeable(self.directory):
                    msg = "Directory is not writable: "
                else:
                    msg = "Unknown Directory error: "

                msg += self.directory

            return AMSReturnCode(self.sig_file, res, msg)

        except Exception as e:
            self.AMSLogger.error('Failed to touch file due to exception: %s' % str(e))
            raise

    def instructions_for_verification(self):
        ret_str = 'Verify the following directory exists and can be read and written to: %s' % str(self.directory) + os.linesep
        ret_str += 'And that directory contains the following filename: %s' % os.path.basename(self.AMSCompleteHandler.complete_handler)
        return ret_str
