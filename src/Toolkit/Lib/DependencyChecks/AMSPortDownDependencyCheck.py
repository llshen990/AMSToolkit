import socket
import sys

import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.DependencyChecks import AbstractAMSDependencyCheck
from Toolkit.Lib.AMSReturnCode import AMSReturnCode

class AMSPortDownDependencyCheck(AbstractAMSDependencyCheck):
    """
    Will ensure that the service end point is not accepting connections
    """

    def __init__(self, ams_config, ams_dependency_checker):
        """
        :param ams_config:
        :type:  AMSConfig
        :param ams_dependency_checker:
        :type: AMSDependencyChecker
        """
        AbstractAMSDependencyCheck.__init__(self, ams_config, ams_dependency_checker)
        data = self.AMSDependencyChecker.dependency.split(':')
        self.host = data[0].strip()
        self.port = data[1].strip()

    def _check_dependency(self):
        """
        This checks the dependency and returns true if it is successful and false otherwise.
        :return:
        :type: AMSReturnCode
        """
        res = False
        msg = "Dependency check " + self.AMSDependencyChecker.dependency
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((self.host, int(self.port)))
            if result == 0:
                print self.host, ":", self.port, " is open"
                res = False
                msg = msg + " " + self.host, ":", self.port, " is open"
            else:
                print self.host, ":", self.port, " is not open"
                msg = msg + " " + self.host, ":", self.port, " is not open"
                res = True
            return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)

        except Exception as e:
            msg = msg + ": " + e.message
            return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)

    def instructions_for_verification(self):
        ret_str = 'The below command should time out or say connection refused:%s' % os.linesep
        ret_str += 'telnet %s %s' % (self.host, self.port)
        return ret_str

    def commandline_output(self):
        return 'The below host should be down:{}{} on port {}'.format(os.linesep,self.host, self.port)