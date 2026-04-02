import os.path, sys, subprocess, ConfigParser

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from lib.Exceptions import ManifestCreateException

class ManifestCreate(object):
    """
    This class will create a manifest file for the given source file.
    Attributes:
        file: string - source file
        manifest_create_script: path to manifest creation script
    """

    def __init__(self, file_to_create_manifest_from):
        """
        ManifestCreate constructor
        Args:
            file_to_create_manifest_from: string
        """
        file_exists_validator = FileExistsValidator(True)
        if not file_exists_validator.validate(file_to_create_manifest_from):
            raise ManifestCreateException('File to create manifest from does not exist: ' + file_to_create_manifest_from)

        self.file = file_to_create_manifest_from

        # set some defaults / setup some config data
        config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        self.manifest_create_script = None

        if config.has_option('DEFAULT', 'manifest_create_script'):
            self.manifest_create_script = config.get('DEFAULT', 'manifest_create_script')
        else:
            raise ManifestCreateException('Config does not contain manifest_create_script (path to manifest creation script)')

        if not file_exists_validator.validate(self.manifest_create_script):
            raise ManifestCreateException('Manifest script does not exist: ' + self.manifest_create_script)

    def create_manifest(self):
        """
        Executes the manifest script
        Returns: Null
        """
        std_out = None
        std_err = None
        sub_process_cmds = [self.manifest_create_script, '-f', self.file]
        p = subprocess.Popen(sub_process_cmds, stdout=std_out, stderr=std_err)
        p.wait()
        if std_err:
            raise ManifestCreateException('Exception create_manifest(std_err): ' + str(std_err).strip())