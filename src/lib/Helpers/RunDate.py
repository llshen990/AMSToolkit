import ConfigParser
import glob
import os.path
import sys
from datetime import datetime, timedelta

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Signals import Signal
from lib.Exceptions import RunDateException

class RunDate(object):
    """
    This class will manage run dates for a specific file type
    """

    def __init__(self, automation_name, signal_sub_folder, date_format='%Y%m%d'):
        # example: dailycycle_transaction_date_20170128.txt
        ###### get config options ######
        self.config = ConfigParser.ConfigParser()
        self.config.read(APP_PATH + '/Config/ssod_validator.cfg')

        if self.config.has_option('DEFAULT', 'file_get_trans_date'):
            self.base_automation_signal_path = self.config.get('DEFAULT', 'base_automation_signal_path')
        else:
            raise Exception('Config does not have base_automation_signal_path config option.')
        ###### end config options ######

        automation_name = str(automation_name).strip()
        if automation_name is None or automation_name == '':
            raise Exception('Automation name required.')

        signal_sub_folder = str(signal_sub_folder).strip()
        if signal_sub_folder is None or signal_sub_folder == '':
            raise Exception('Signal sub folder required.')

        self.automation_name = automation_name
        self.signal_sub_folder = signal_sub_folder
        self.date_format = date_format
        self.last_run_date_signal = None  # type: Signal
        self.last_run_date = None
        self.last_run_date_obj = None  # type: datetime
        self.current_run_date = None
        self.current_run_date_obj = None  # type: datetime
        self.current_run_date_signal = None  # type: Signal
        self.next_run_date_signal = None  # type: Signal
        self.next_run_date = None
        self.next_run_date_obj = None  # type: datetime
        self.signal_directory = os.path.join(self.base_automation_signal_path, self.signal_sub_folder)
        if not os.path.exists(self.signal_directory):
            os.makedirs(self.signal_directory)

    def get_last_run_date(self):
        """
        This method will get and set some member variables associated with the last run date of a batch.
        :return: True upon success
        :rtype: bool
        """
        try:
            for latest_file in sorted(glob.glob1(self.signal_directory, self.automation_name + '*.txt'), reverse=True):
                last_run_date = str(str(latest_file).replace(self.automation_name + '_', '').replace('.txt', '')).strip()
                self.last_run_date_obj = datetime.strptime(last_run_date, self.date_format)
                if self.last_run_date_obj.strftime(self.date_format) != last_run_date:
                    raise RunDateException('Last transaction date does match proper format: ' + last_run_date + ' -> ' + self.date_format)
                full_file_path = os.path.join(self.signal_directory, latest_file.strip())
                self.last_run_date_signal = Signal(os.path.dirname(full_file_path), os.path.basename(full_file_path), True, '.txt')
                self.last_run_date = int(last_run_date)
                return True
            exception_msg = 'Could not determine last date run.  Please make sure there is at least one file in' + self.signal_directory
            exception_msg += '.  The file should be the date immediately prior to the first day of automation.  Ex: ' + os.path.join(self.signal_directory, self.automation_name + '_' + datetime.now().strftime(self.date_format) + '.txt')
            raise RunDateException(exception_msg)
        except Exception as e:
            raise RunDateException(str(e))

    def get_current_run_date(self):
        """
        This method will attempt to get the current run date of a batch automation based upon the signal files.
        :return: True upon success.
        :rtype: bool
        """
        try:
            if not self.last_run_date:
                self.get_last_run_date()

            date_object_last = datetime.strptime(str(self.last_run_date), self.date_format)
            self.current_run_date_obj = date_object_last + timedelta(days=1)
            self.current_run_date = self.current_run_date_obj.strftime(self.date_format)
            self.current_run_date_signal = Signal(self.signal_directory, self.automation_name + '_' + str(self.current_run_date) + '.txt', True, '.txt')

            self.next_run_date_obj = date_object_last + timedelta(days=2)
            self.next_run_date = self.next_run_date_obj.strftime(self.date_format)
            self.next_run_date_signal = Signal(self.signal_directory, self.automation_name + '_' + str(self.next_run_date) + '.txt', True, '.txt')
            return True
        except Exception as e:
            raise RunDateException(str(e))