import os.path, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator, DateValidator
from lib.Helpers import FileGetTransDate

class MaxTransactionDate(object):
    """
    This class will determine the max transaction date allowed to be in a file based on filename.
    """

    def __init__(self, file_name):
        """
        Initializes MaxTransactionDate class
        Args:
            file_name: string - 'my' filename.
        """

        self.file_name = file_name

        file_exists_validator = FileExistsValidator(True)
        if not file_exists_validator.validate(self.file_name):
            raise Exception('File: ' + self.file_name + ' does not exist')

    def get_tran_date(self, mode='max'):
        """
        This method will get the max trans date and return it.
        Returns: string
        """

        if mode not in ['max', 'min']:
            raise Exception('Invalid mode passed to get_tran_date')

        file_get_date = FileGetTransDate()
        tran_date = file_get_date.get_trans_date_from_filename(self.file_name, mode)
        date_format_str = "%Y%m%d %H:%M:%S"
        tran_date_str = tran_date.strftime(date_format_str)
        date_validator = DateValidator(True)
        options = {
            "format": date_format_str
        }
        if not date_validator.validate(tran_date_str, options):
            raise Exception('Invalid transaction date: ' + date_validator.format_errors())

        return tran_date