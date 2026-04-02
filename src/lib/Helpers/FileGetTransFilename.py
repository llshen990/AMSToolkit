import os.path, sys, subprocess, ConfigParser

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import DateValidator, StrValidator
from lib.Exceptions import SkipValidationException

class FileGetTransFilename(object):
    """
    This class is a wrapper for the ssoaid/bin/file_get_trans_filename.sh script.
    """

    def __init__(self):
        # get config options
        self.config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        self.config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        if self.config.has_option('DEFAULT', 'file_get_trans_filename'):
            self.file_get_trans_filename_script = self.config.get('DEFAULT', 'file_get_trans_filename')
        else:
            raise Exception('Config does not have file_get_trans_filename config option.')
        if self.config.has_option('DEFAULT', 'landingdir'):
            self.landing_dir = self.config.get('DEFAULT', 'landingdir')
        else:
            raise Exception('Config does not have landingdir config option.')
            # end config

    def get_file_name_from_type(self, file_type, date=None):
        """
        This method will return a file pattern of the desired file type.  It will default to the
        current run date unless date is passed in.
        Args:
            file_type: string
            date: string
        Returns: String
        """

        process_list = [self.file_get_trans_filename_script, "-f", file_type]

        if date:
            date_validator = DateValidator(True)
            options = {
                "format": "%Y%m%d"
            }
            if not date_validator.validate(date, options):
                raise Exception('Invalid date: ' + date_validator.format_errors())
            process_list.append('-d')
            process_list.append(date)

        process_list.append('-p')

        p = subprocess.Popen(process_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tmp_std_out, tmp_std_err = p.communicate()
        tmp_std_out = tmp_std_out.strip()
        tmp_std_err = tmp_std_err.strip()
        str_validator = StrValidator(True)
        if not str_validator.validate(tmp_std_out) or tmp_std_err != '':
            raise Exception('[' + self.file_get_trans_filename_script + ' ' + file_type + ']: ' + tmp_std_err.strip() + ' - ' + tmp_std_out)
        elif tmp_std_out == 'NOT FOUND':
            raise SkipValidationException('Could not find dependent related file for ' + file_type + '.  File likely has not been delivered yet.')
        return self._find_file_from_pattern(tmp_std_out)

    def _find_file_from_pattern(self, pattern):
        """
        This method will find the exact file based on pattern in /sso/transport/incoming
        Args:
            pattern:

        Returns:

        """
        # print 'pattern: ' + pattern
        process_list = ["find", "-L", self.landing_dir, "-maxdepth", "1", "-name", pattern]
        p = subprocess.Popen(process_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tmp_std_out, tmp_std_err = p.communicate()
        if tmp_std_err:
            raise Exception('Errors running ' + self.file_get_trans_filename_script + ' ' + pattern + ': ' + tmp_std_err.strip())

        tmp_std_out_clean = tmp_std_out.strip()
        # print 'tmp_std_out_clean: ' + tmp_std_out_clean
        filename_split = tmp_std_out_clean.split(os.linesep)
        num_files_found = len(filename_split)
        # print 'num_files_found: ' + str(num_files_found)
        if num_files_found != 1:
            raise Exception('Expecting only one file for pattern ' + pattern + '.  ' + str(num_files_found) + ' files were found: ' + ",".join(filename_split))
        return tmp_std_out_clean
