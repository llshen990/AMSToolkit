import os.path, sys, subprocess, socket

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import *
from lib.Exceptions import *

class DecryptPgP(object):
    """ This class will decrypt a file and clean itself up upon destruction
    Attributes:
        file_to_decrypt: The file to be decrypted
        decrypt_script_path: The path to the executable that will decrypt *file_to_decrypt*
        hostname: Hostname of server running.
        decrypted_file_path: The path of the decrypted file after it has been decrypted
        decrypt_execution_output: The output of the decrypt execution of trying to decrypt file.
        decrypt_error_output: The error output of the decrypt execution.
    """

    def __init__(self, file_to_decrypt, decrypt_script_path):
        """
        :param file_to_decrypt: string
        :param decrypt_script_path: string
        :return: DecryptPgP
        """
        self.file_to_decrypt = str(file_to_decrypt).strip()
        self.decrypt_script_path = str(decrypt_script_path).strip()
        self.hostname = str(socket.gethostname()).strip()
        if self.hostname == 'sasdev1-centos6':
            self.decrypt_script_path = '/home/devshare/python/SAS/general_op_scripts/bash_scripts/utilities/decrypt.sh'
        self.decrypted_file_path = ''
        self.decrypt_execution_output = ''
        self.decrypt_error_output = ''
        self.shred_on_del = True

        file_validator = FileExistsValidator(True)
        if not (file_validator.validate(self.file_to_decrypt)) or not (file_validator.validate(self.decrypt_script_path)):
            raise DecryptPgPException('File to decrypt is not exist or has improper permissions: ' + self.file_to_decrypt)

        # self.decrypt_execution_output = os.popen(self.decrypt_script_path + " " + self.file_to_decrypt).read()
        old_std_err = sys.stderr
        try:
            sys.stderr = sys.stdout
            p = subprocess.Popen([self.decrypt_script_path, self.file_to_decrypt], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.decrypt_execution_output, self.decrypt_error_output = p.communicate()
            if self.decrypt_error_output and self.hostname not in ['sasdev1-centos6']:
                raise DecryptPgPException(str(self.decrypt_error_output).strip())
        except Exception as e:
            raise DecryptPgPException('Could not decyrpt the ' + self.file_to_decrypt + ' due to: ' + str(e) + ' - ' + str(self.decrypt_execution_output).strip())
        finally:
            sys.stderr = old_std_err
            self.decrypted_file_path = self.file_to_decrypt.replace('.pgp', '').replace('.asc', '')

    def __del__(self):
        """This is the destructor for DecryptPgP.  It will shred the file i.e. securely delete it."""
        if not self.shred_on_del:
            return True
        file_validator = FileExistsValidator(True)
        if file_validator.validate(self.decrypted_file_path):
            from lib.Helpers import FileShredder
            FileShredder(self.decrypted_file_path)

        return True