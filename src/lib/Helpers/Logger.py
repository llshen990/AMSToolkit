# @author owhoyt
import sys, os

from lib.Validators import FileExistsValidator

class Logger(object):
    """ This is a logger object that will log to both a file + std out.

    Attributes:
        log_file: log file path
        terminal: sys.stdout --> log to stdout
        log: the log file object
        closed: if the file has been closed or not
    """

    def __init__(self, log_file):
        file_exists_validator = FileExistsValidator(True)
        self.log_file = log_file
        self.terminal = sys.stdout
        self.log = open(log_file, "a")
        self.closed = False
        if not file_exists_validator:
            raise Exception('File could not be opened for writing: ' + log_file)

    def write(self, message):
        self.terminal.write(message)
        if not self.closed:
            self.log.write(message)

    def write_debug(self, message, debug):
        if debug:
            self.terminal.write(message)

        if not self.closed:
            self.log.write(message)

        return True

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass

    def close_logger(self):
        if not self.closed:
            self.closed = True
            self.log.close()

    def get_log_file_contents(self):
        if not self.closed:
            raise Exception('Log file cannot be read as it is still open for writing!')

        with open(self.log_file, 'r') as my_file:
            file_contents = my_file.read()

        return str(file_contents).strip()

    def __del__(self):
        if not self.closed:
            self.closed = True
            self.log.close()