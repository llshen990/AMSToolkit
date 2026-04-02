import os
import subprocess
import logging
import datetime
import tempfile

from lib.Validators import FileExistsValidator

class ProcCheck(object):
    """
    This method will ensure that a script (process) cannot be running more than one instance at a time.
    Attributes:
        lock_file_name: The location of the lock file.
    """

    def __init__(self, controller_name, context, lock_dir=os.getcwd(), user_in_lock_file=True):
        """
        This method will construct the ProcCheck class.
        Args:
        """
        # Ensure the user can access the lock_dir
        if not FileExistsValidator.directory_writeable(lock_dir):
            logging.getLogger('AMS').warning('The lock dir {} provided is not writable, defaulting to {}'.format(lock_dir, tempfile.gettempdir()))
            lock_dir = tempfile.gettempdir()

        self.lock_file_name = ProcCheck.get_lock_file_name(controller_name, context, lock_dir, user_in_lock_file)
        self._lock_success = False

    def lock_file_present(self):
        logging.getLogger('AMS').info("Checking for existing lock file {}".format(self.lock_file_name))
        return FileExistsValidator.is_readable(self.lock_file_name)

    @staticmethod
    def get_lock_file_name(controller_name, context, lock_dir=os.getcwd(), user_in_lock_file=True):
        user_name = ''
        if user_in_lock_file:
            if not os.environ.get('_USER'):
                user_name = subprocess.check_output('whoami').strip()
            else:
                user_name = os.environ['_USER']

        lock_context = '__' + os.path.basename(controller_name) + '_' + str(context).replace(os.path.sep, '_') + '_' + user_name + '__.lock'

        return os.path.join(os.path.abspath(lock_dir), lock_context)

    def lock(self):
        """
        This method will write the lock file with the pid of the singularly running process.
        :param pid: int
        :return: bool
        """
        try:
            logging.getLogger('AMS').info("Checking for existing lock file {}".format(self.lock_file_name))
            if os.path.isfile(self.lock_file_name):
                logging.getLogger('AMS').error("Existing lock file {}".format(self.lock_file_name))
                return False

            logging.getLogger('AMS').debug("Lock file {} does not exist".format(self.lock_file_name))

            logging.getLogger('AMS').debug("Locking file {}".format(self.lock_file_name))
            f = open(self.lock_file_name, 'w')
            pid = str(os.getpid())
            f.write('Pid {} started at {}\n'.format(pid, datetime.datetime.now()))
            cmdline_file = '/proc/{}/cmdline'.format(pid)
            if os.path.isfile(cmdline_file):
                with open(cmdline_file, 'r') as contents:
                    f.write('CmdLine={}'.format(contents.read()))
            f.write('Environ={}\n'.format(os.environ))
            f.close()
            logging.getLogger('AMS').info("Wrote lock file {}".format(self.lock_file_name))
            self._lock_success = True
            return True
        except Exception as e:
            logging.getLogger('AMS').error("Caught exception writing lock file {}".format(e))
            return False

    def unlock(self):
        try:
            if self._lock_success:
                logging.getLogger('AMS').debug("Unlocking lock file {}".format(self.lock_file_name))
                os.remove(self.lock_file_name)
                logging.getLogger('AMS').info("Removed lock file {}".format(self.lock_file_name))
                return True
            else:
                logging.getLogger('AMS').info("Not unlocking lock file {} because it wasn't locked by us".format(self.lock_file_name))
                return False
        except Exception as e:
            logging.getLogger('AMS').error('Error removing lock file {}'.format(e))
            return False
