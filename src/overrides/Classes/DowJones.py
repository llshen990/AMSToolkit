import os.path, sys, shutil, ConfigParser, time

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from lib.Helpers import Compressor, EncodingHelper
from lib.Validators import FileExistsValidator
from lib.Exceptions import SuccessfulStopValidationException

class DowJones(object):
    def __init__(self, encoding, file_name):
        self.encoding = encoding.strip()
        self.encoder = None
        self.file_name = file_name.strip()
        self.file_exists_validator_obj = FileExistsValidator(True)
        if not self.file_exists_validator_obj.validate(self.file_name):
            raise Exception('DowJones Exception __init__: file does not exist: ' + self.file_name)
        self.compressor_obj = Compressor(self.file_name)

        self.archive_folder_name = 'Factiva_PFA_Feed_CSV'

        basename_tmp = os.path.basename(self.file_name)
        self.decompressed_filename = self.archive_folder_name + '/' + basename_tmp.upper().replace('.ZIP', '.csv')

        self.archive_zip_name = os.path.basename(file_name)
        self.orig_file_path = os.path.dirname(self.file_name)

        # set some defaults / setup some config data
        self.config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        self.config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        self.backup_folder = ''
        self.time_stamped_backup_folder = None
        if self.config.has_option('DEFAULT', 'orig_file_backup_location'):
            self.backup_folder = self.config.get('DEFAULT', 'orig_file_backup_location')
        else:
            raise Exception('Could not __init__ EncodingHelper: Backup folder is not defined in the config.')

        self.debug = False
        if self.config.has_option('DEFAULT', 'debug'):
            self.debug = self.config.getboolean('DEFAULT', 'debug')

    def validate_file(self):
        unarchived_file = self.compressor_obj.get_temp_path() + '/' + self.decompressed_filename

        self._backup_orig_file()

        self._print_msg('Decompressing Dow Jones file: ' + self.file_name)
        self.compressor_obj.unzip()

        self._print_msg('Doing Conversion to ' + self.encoding + ' on ' + unarchived_file)

        self.encoder = EncodingHelper(unarchived_file)
        self.encoder.set_final_backup_folder(self.time_stamped_backup_folder)
        self.encoder.set_has_external_orig_file_backup()
        self.encoder.set_no_diff_report()
        self.encoder.set_no_manifest()
        self.encoder.set_no_encrypt()
        self.encoder.set_custom_email_msg('No diff report can be created for the dow jones file as it comes in as a UTF-16 format')
        self.encoder.convert_file_encoding(self.encoding)

        new_archive_folder = self.compressor_obj.get_temp_path() + '/' + self.archive_folder_name

        if not os.path.exists(new_archive_folder):
            os.makedirs(new_archive_folder)

        # shutil.copy(encoder.get_encoded_filename(), new_archive_folder)
        zip_file_name = self.compressor_obj.get_temp_path() + '/' + self.archive_zip_name
        self.compressor_obj.zip_dir(zip_file_name, new_archive_folder)

        os.remove(self.file_name)
        shutil.move(zip_file_name, self.orig_file_path)
        self.compressor_obj.delete()

        raise SuccessfulStopValidationException('Successfully validated Dow Jones File')

    def _backup_orig_file(self):
        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)

        self.time_stamped_backup_folder = self.backup_folder + '/' + (time.strftime('%Y%m%d_%H%M'))
        if not os.path.exists(self.time_stamped_backup_folder):
            os.makedirs(self.time_stamped_backup_folder)

        self._print_msg('Backing up orig file: ' + self.file_name + ' to backup location: ' + self.time_stamped_backup_folder)

        shutil.copy(self.file_name, self.time_stamped_backup_folder)

    def _print_msg(self, msg):
        if self.debug:
            print str(msg)