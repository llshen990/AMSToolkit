import os.path, sys, subprocess, ConfigParser

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator

class BatchTriggers(object):
    """ This class will handle creating or destroying batch trigger files.
    Attributes:
        batch_delay_trigger_file: Creation (presence) of this file will trigger a batch delay.
    """

    def __init__(self):
        """
        :return: BatchTriggers
        """
        # set some defaults / setup some config data
        config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        self.batch_delay_trigger_file = ''
        if config.has_option('DEFAULT', 'batch_delay_trigger_file'):
            self.batch_delay_trigger_file = config.get('DEFAULT', 'batch_delay_trigger_file')

    def create_batch_delay_trigger_file(self):
        """ This method will create the *batch_delay_trigger_file* file on the file system if it does not already exist
        :return: none
        """
        self._create_trigger_file(self.batch_delay_trigger_file)

    def delete_batch_delay_trigger_file(self):
        """ This method will delete the *batch_delay_trigger_file* file from the file system if it exists.
        :return: none
        """
        self._delete_trigger_file(self.batch_delay_trigger_file)

    def _create_trigger_file(self, path):
        """ This method will create the *path* if it does not exist on the file system already.
        :param path: string
        :return: bool
        """
        if not self.batch_delay_trigger_file:
            raise Exception('Could not create batch trigger file as none was defined!')

        file_validator = FileExistsValidator()
        if not (file_validator.validate(path)):
            create_file_output = str(os.mknod(path)).strip()
            if not create_file_output or create_file_output == 'None':
                return True

            raise Exception('Could not create the batch trigger file: ' + self.batch_delay_trigger_file)

        return True

    def _delete_trigger_file(self, path):
        """ This method will remove the *path* from the file system if it exists.
        :param path: string
        :return: bool
        """
        file_validator = FileExistsValidator()
        if file_validator.validate(path):
            p = subprocess.Popen(['rm', '-f', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            rm_output, rm_output_err = p.communicate()
            if (not rm_output or rm_output == 'None') and (not rm_output_err or rm_output_err == 'None'):
                return True
            else:
                raise Exception('Could not delete the batch trigger file: ' + rm_output + ' - ' + rm_output_err)

        return True