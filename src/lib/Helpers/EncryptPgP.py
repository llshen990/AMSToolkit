import os.path, sys, subprocess, ConfigParser

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from lib.Exceptions import *

class EncryptPgP(object):
    """
    EncryptPgP encrypts a file.
    Attributes:
        encrypt_script: path to the script that performs the actual encryption.
        file: file that we're trying to encrypt
    """

    def __init__(self, file_to_encrypt):
        """
        Constructor for EncryptPgP
        Args:
            file_to_encrypt: string - input file to encrypt
        """

        file_exists_validator = FileExistsValidator(True)
        if not file_exists_validator.validate(file_to_encrypt):
            raise EncryptPgPException('File to encrypt from does not exist: ' + file_to_encrypt)

        self.file = file_to_encrypt

        # set some defaults / setup some config data
        config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        self.encrypt_script = None

        if config.has_option('DEFAULT', 'encrypt_script'):
            self.encrypt_script = config.get('DEFAULT', 'encrypt_script')
        else:
            raise EncryptPgPException('Config does not contain encrypt_script (path to encrypt script)')

        if not file_exists_validator.validate(self.encrypt_script):
            raise EncryptPgPException('Encrypt script does not exist: ' + self.encrypt_script)

    def encrypt(self):
        """
        Actually performs the encryption of the input file.
        Returns: null
        """
        std_out = None
        std_err = None
        sub_process_cmds = [self.encrypt_script, self.file]
        p = subprocess.Popen(sub_process_cmds, stdout=std_out, stderr=std_err)
        p.wait()
        if std_err:
            raise EncryptPgPException('Exception encrypt(std_err): ' + str(std_err).strip())