__author__ = "Scott Greenberg"
__email__ = "scott.greenberg@sas.com"

from ..AMSScriptReturnCode import AMSScriptReturnCode
from subprocess import Popen, PIPE
from socket import gethostname


class MSSsh(object):
    # This class serves as a generic interface for issuing bash commands over ssh or executing commands on localhost.

    @staticmethod
    def runcmd(command, host=None):
        """
        execute command over ssh and get output/errors
        Args:
            host (optional): str, hostname to ssh to, if this isn't specified then we run command on localhost
            command: str, bash command to run
        Returns: tuple (stdout or stderr, return code)
        """
        if type(command) != list:
            command = command.split(' ')
            # use localhost if no remote host is provided
            host = host or gethostname()
            # make command into ssh command to host if not localhost
        if host != gethostname():
            command = ['ssh', host] + command
        cmd = Popen(command, shell=False, stdout=PIPE, stderr=PIPE, close_fds=True)
        pid = cmd.pid
        result = cmd.stdout.read()
        errors = cmd.stderr.read()
        return_object = AMSScriptReturnCode(pid, 0, result, errors, 'runcmd')
        # if the result is blank we know output was routed to stderr
        if not return_object.std_out:
            return_object.returncode = 1
        return return_object

