import os.path, sys, subprocess, ConfigParser, signal

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import StrValidator, FileExistsValidator
from lib.Exceptions import FileValidateTransDateException

class FileValidateTransDate(object):
    """
    This class is a wrapper for the ssoaid/bin/file_validate_trans_date.sh script.
    """

    def __init__(self, file_name):
        # get config options
        self.config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        self.config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        if self.config.has_option('DEFAULT', 'file_validate_trans_date'):
            self.file_validate_trans_date = self.config.get('DEFAULT', 'file_validate_trans_date')
        else:
            raise Exception('Config does not have file_validate_trans_date config option.')
            # end config

        self.file_name = file_name

        file_exists_validator = FileExistsValidator(True)
        if not file_exists_validator.validate(self.file_name):
            raise Exception('File: ' + self.file_name + ' does not exist')

    @staticmethod
    def default_sigpipe():
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    def validate_trans_date_from_filename(self):
        """
        This method will return a the file type from the filename.
        Returns: string
        """

        try:
            p = subprocess.Popen([self.file_validate_trans_date, "-f", os.path.basename(self.file_name)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.default_sigpipe)
            tmp_std_out, tmp_std_err = p.communicate()
            tmp_std_out = tmp_std_out.strip()
            tmp_std_err = tmp_std_err.strip()
            str_validator = StrValidator(True)
            if not str_validator.validate(tmp_std_out) or tmp_std_out == 'INVALID' or tmp_std_out == 'NOT FOUND':
                raise FileValidateTransDateException(os.path.basename(self.file_name) + ' is an invalid filename or is from a transaction date that has already been processed by the system.')

            if not str_validator.validate(tmp_std_out) or tmp_std_out != 'VALID' or tmp_std_err != '':
                raise Exception('Errors running ' + self.file_validate_trans_date + ' ' + os.path.basename(self.file_name) + ': ' + tmp_std_err.strip() + ' - ' + tmp_std_out)

            return str(tmp_std_out).strip()
        except FileValidateTransDateException:
            raise
        except Exception as e:
            # print 'Transaction Date For File Is: ' + str(e)
            raise FileValidateTransDateException(e)