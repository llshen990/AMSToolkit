import os.path, sys, subprocess, ConfigParser, re

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import StrValidator, DateValidator


class UpdateBatchStatus(object):
    """
    This class is a wrapper for the ssoaid/bin/sso_update_batch_status.sh script.
    """

    def __init__(self):
        # get config options
        self.config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        self.config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        if self.config.has_option('DEFAULT', 'sso_update_batch_status'):
            self.sso_update_batch_status = self.config.get('DEFAULT', 'sso_update_batch_status')
        else:
            raise Exception('Config does not have sso_update_batch_status config option.')
            # end config

        self.calling_script = None
        self.status = None
        self.information = None
        self.agp_run_date = None
        self.batch_group = None
        self.error_pattern_list = ["ERROR:", '"ERROR:']

    def update_batch_status(self, calling_script, status, information, agp_run_date='', batch_group='DAILY_CYCLE'):
        """
        This method will update the batch status in the data store
        Args:
            calling_script: string
            status: string
            information: string
            agp_run_date: string
            batch_group: string
        Returns: string
        """

        try:

            self.calling_script = str(calling_script).strip()
            self.status = str(status).strip().upper()
            self.information = str(information).strip()
            self.agp_run_date = str(agp_run_date).strip()
            self.batch_group = str(batch_group).strip().upper()

            if not self.calling_script:
                raise Exception('Calling script required.')

            if not self.status:
                raise Exception('status required.')

            if not self.information:
                raise Exception('Information required.')

            if not self.batch_group:
                raise Exception('Batch group required.')

            if self.agp_run_date:
                d = DateValidator(True)
                if not d.validate(self.agp_run_date, {"format": '%Y%m%d'}):
                    raise Exception('Invalid AGP Run Date: ' + self.agp_run_date + ".  Must be in yyyymmdd format.")

            if self.batch_group not in ['DAILY_CYCLE', 'WATCHLIST', 'USD_REPORT']:
                raise Exception('Invalid batch group: ' + self.batch_group)

            args_list = [
                self.sso_update_batch_status,
                "-n",
                self.calling_script,
                "-s",
                self.status,
                "-i",
                self.information,
                "-d",
                self.agp_run_date,
                "-b",
                self.batch_group
            ]
            p = subprocess.Popen(args_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tmp_std_out, tmp_std_err = p.communicate()
            tmp_std_out = tmp_std_out.strip()
            tmp_std_err = tmp_std_err.strip()
            str_validator = StrValidator(True)

            pattern = re.compile('|'.join(self.error_pattern_list))
            errors = pattern.findall(tmp_std_out)

            if not str_validator.validate(tmp_std_out) or tmp_std_err != '':
                raise Exception('Errors running ' + self.sso_update_batch_status + ' ' + calling_script + ': ' + tmp_std_err.strip() + ' - ' + tmp_std_out)
            elif len(errors) > 0:
                raise Exception('Errors running ' + self.sso_update_batch_status + ' ' + calling_script + ': ' + tmp_std_out.strip())

            return str(tmp_std_out).strip()
        except Exception as e:
            print 'sso_update_batch_status Exception: ' + str(e)
            raise Exception(e)
