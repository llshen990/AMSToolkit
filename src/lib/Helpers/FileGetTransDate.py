import ConfigParser
import os.path
import subprocess
import sys
from datetime import datetime

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import StrValidator

class FileGetTransDate(object):
    """
    This class is a wrapper for the ssoaid/bin/file_get_trans_date.sh script.
    """

    def __init__(self):
        # get config options
        self.config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        self.config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        if self.config.has_option('DEFAULT', 'file_get_trans_date'):
            self.file_get_trans_date = self.config.get('DEFAULT', 'file_get_trans_date')
        else:
            raise Exception('Config does not have file_get_trans_filename config option.')
            # end config

    def get_trans_date_from_filename(self, file_name, mode='max'):
        """
        This method will return a the transaction date of a source file given the filename.
        Args:
            file_name: string
            mode: string
        Returns: datetime object
        """

        if mode not in ['min', 'max']:
            raise Exception('Invalid mode passed to get_trans_date_from_filename')

        try:
            # @todo - remove 1st return command:
            # return datetime.strptime('20170319 23:59:59', '%Y%m%d %H:%M:%S')
            p = subprocess.Popen([self.file_get_trans_date, "-f", file_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tmp_std_out, tmp_std_err = p.communicate()
            tmp_std_out = tmp_std_out.strip()
            tmp_std_err = tmp_std_err.strip()
            str_validator = StrValidator(True)
            if not str_validator.validate(tmp_std_out) or tmp_std_out == 'NOT FOUND' or tmp_std_err != '':
                raise Exception('Errors running ' + self.file_get_trans_date + ' ' + file_name + ': ' + tmp_std_err.strip() + ' - ' + tmp_std_out)

            if mode == 'max':
                tmp_std_out += ' 23:59:59'
            else:
                tmp_std_out += ' 00:00:00'

            return datetime.strptime(tmp_std_out, '%Y%m%d %H:%M:%S')
        except Exception as e:
            print 'get_trans_date_from_filename Exception: ' + str(e)
            raise Exception(e)