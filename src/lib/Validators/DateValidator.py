# @author owhoyt
from AbstractValidator import AbstractValidator
from datetime import datetime

import os.path, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from BoolValidator import BoolValidator

# look at https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior for formats
class DateValidator(AbstractValidator):
    """This class validates a date"""

    def __init__(self, debug=False):
        """ Instantiates an DateValidator object
        :param debug: bool
        :return: DateValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is an float

        :type data_input: mixed
        :param data_input: Input to validate
        :param options: Object of options if any are passed
        :return: bool
        """
        try:
            is_valid = True
            if options is None or 'format' not in options:
                self.add_error('N/A', 'Must pass in format for date field.')
                return False

            is_digit = self._is_number(data_input)

            if is_digit:
                data_input = str(data_input)
            else:
                data_input = data_input.encode('UTF-8')

            date_object = datetime.strptime(data_input, options['format'])

            # this is a hack for WMT who keeps sending in dates prior to 1900.
            bool_validator = BoolValidator(self.debug)
            date_hack = False
            if 'dateHack' in options and bool_validator.validate(options['dateHack']) and options['dateHack']:
                date_hack = True

            data_input_orig = data_input
            if date_hack and date_object.year < 1900:
                data_input = str(data_input).replace(str(date_object.year), '1900', 1)
                date_object = date_object.replace(year=1900)

            print date_object.strftime(options['format'])
            print data_input

            if date_object.strftime(options['format']) != data_input:
                self.add_error(data_input_orig, 'Invalid input date')
                is_valid = False

            if 'max' in options and options['max'] != '':
                if isinstance(options['max'], datetime):
                    max_dt_obj = options['max']
                else:
                    max_dt_obj = datetime.strptime(options['max'], options['format'])

                if max_dt_obj < date_object:
                    self.add_error(data_input_orig, 'must be <= ' + str(options['max']) + '.')
                    is_valid = False

            if 'min' in options and options['min'] != '':
                if isinstance(options['min'], datetime):
                    min_dt_obj = options['min']
                else:
                    min_dt_obj = datetime.strptime(options['min'], options['format'])

                if min_dt_obj > date_object:
                    self.add_error(data_input_orig, 'must be >= ' + str(options['min']) + '.')
                    is_valid = False

            if not is_valid:
                return False
        except Exception as e:
            self.add_error(str(e), "is not a valid date")
            return False
        return True