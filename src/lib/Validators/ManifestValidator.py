import ConfigParser
import mmap
import os.path
import sys
import traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from AbstractValidator import AbstractValidator
from lib.Validators import FileExistsValidator

class ManifestValidator(AbstractValidator):
    """
    This class will validate a manifest and file combination.
    """

    def __init__(self, debug=True):
        """"
        Instantiates an ManifestValidator object
        """
        AbstractValidator.__init__(self, debug)

        ###### get config options ######
        self.config = ConfigParser.ConfigParser()
        self.config.read(APP_PATH + '/Config/ssod_validator.cfg')

        if self.config.has_option('DEFAULT', 'decrypt_script'):
            self.decrypt_script = self.config.get('DEFAULT', 'decrypt_script')
        else:
            raise Exception('Config does not have decrypt_script config option.')

        ###### end config options ######
        self.file = None  # type: str
        self.manifest = None  # type: str
        self.decrypted_manifest_path = None  # type: str
        self.decrypted_file_path = None  # type: str
        self.expected_filename = None
        self.expected_row_count = None
        self.expected_md5 = None
        self.actual_row_count = None
        self.actual_md5 = None

    def validate(self, data_input, options=None):
        """
        This method will validate a Manifest and File combination with data_input = manifest and options = filename.
        :param data_input: This is the path to the Manifest file
        :type data_input: str
        :param options: This is the path to the File.
        :type options: str
        :return: True upon success and False on error.
        :rtype: bool
        """
        try:
            from lib.Helpers import DecryptPgP
            self.manifest = str(data_input).strip()
            self.file = str(options).strip()

            if self.manifest == '':
                self.add_error(self.manifest, 'Could not validate manifest and file: manifest path required.')

            if self.file == '':
                self.add_error(self.file, 'Could not validate manifest and file: file path required.')

            fev = FileExistsValidator(True)
            if not fev.validate(self.manifest):
                self.add_error(self.manifest, 'Could not validate manifest and file: manifest does not exist')

            if not fev.validate(self.file):
                self.add_error(self.file, 'Could not validate manifest and file: file does not exist')

            file_decrypter = DecryptPgP(self.file, self.decrypt_script)
            self.decrypted_file_path = file_decrypter.decrypted_file_path
            manifest_decrypter = DecryptPgP(self.manifest, self.decrypt_script)
            self.decrypted_manifest_path = manifest_decrypter.decrypted_file_path

            if not self.get_manifest_details():
                return False

            if not self.get_file_details():
                return False

            return self.compare_manifest_and_file()
        except Exception as e:
            # self.add_error(self.file + '|' + self.manifest, 'Could not validate manifest and file: ' + str(e))
            # return False
            print str(e)
            traceback.print_exc()

    def get_manifest_details(self):
        try:
            with open(self.decrypted_manifest_path, "r") as manifest:
                last_line = None  # type: str
                for line in manifest:
                    # we don't care about any line but the last
                    last_line = line
                last_line = str(last_line).strip()
                formatted_last_line = '|'.join(last_line.split())
                last_line_list = formatted_last_line.split('|')
                tmp_expected_filename = str(last_line_list[1]).strip()
                if tmp_expected_filename.startswith('file.'):
                    self.expected_filename = tmp_expected_filename
                else:
                    self.expected_filename = 'file.' + tmp_expected_filename
                self.expected_row_count = last_line_list[2]
                self.expected_md5 = last_line_list[3]

            return True
        except Exception as e:
            self.add_error(self.manifest, 'Could not get manifest details: ' + str(e))
            return False

    def get_file_details(self):
        try:
            f = open(self.decrypted_file_path, "r+")
            buf = mmap.mmap(f.fileno(), 0)
            self.actual_row_count = 0
            read_line = buf.readline
            while read_line():
                self.actual_row_count += 1

            from lib.Helpers import Md5Sum
            md5_obj = Md5Sum()
            self.actual_md5 = md5_obj.md5_hash_for_file(self.decrypted_file_path)
            return True
        except Exception as e:
            self.add_error(self.decrypted_file_path, 'Could not get file details: ' + str(e))
            return False

    def compare_manifest_and_file(self):
        ret_val = True
        if int(self.actual_row_count) != int(self.expected_row_count):
            self.add_error(str(self.actual_row_count) + ' != ' + str(self.expected_row_count), 'Actual row count != Expected row count')
            ret_val = False

        if self.actual_md5 != self.expected_md5:
            self.add_error(str(self.actual_md5) + ' != ' + str(self.expected_md5), 'Actual md5 != Expected md5')
            ret_val = False

        if os.path.basename(self.decrypted_file_path) != self.expected_filename:
            self.add_error(str(self.file) + ' != ' + str(self.expected_filename), 'Actual filename != Expected filename')
            ret_val = False
        return ret_val