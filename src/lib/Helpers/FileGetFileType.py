import os.path, sys, subprocess, ConfigParser

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import StrValidator

class FileGetFileType(object):
    """
    This class is a wrapper for the ssoaid/bin/file_get_file_type.sh script.
    """

    def __init__(self):
        # get config options
        self.config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        self.config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        if self.config.has_option('DEFAULT', 'file_get_file_type'):
            self.file_get_file_type = self.config.get('DEFAULT', 'file_get_file_type')
        else:
            raise Exception('Config does not have file_get_trans_filename config option.')
            # end config

    def get_file_type_from_filename(self, file_name):
        """
        This method will return a the file type from the filename.
        Args:
            file_name: string
        Returns: string
        """

        try:
            p = subprocess.Popen([self.file_get_file_type, "-f", file_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tmp_std_out, tmp_std_err = p.communicate()
            tmp_std_out = tmp_std_out.strip()
            tmp_std_err = tmp_std_err.strip()
            str_validator = StrValidator(True)
            if not str_validator.validate(tmp_std_out) or tmp_std_out == 'NOT FOUND' or tmp_std_err != '':
                raise Exception('Errors running ' + self.file_get_file_type + ' ' + file_name + ': ' + tmp_std_err.strip() + ' - ' + tmp_std_out)

            return str(tmp_std_out).strip()
        except Exception as e:
            print 'WARNING: get_file_type_from_filename Exception: ' + str(e)
            raise Exception(e)