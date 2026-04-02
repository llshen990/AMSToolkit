# @author owhoyt
from AbstractValidator import AbstractValidator
from decimal import Decimal


class FloatValidator(AbstractValidator):
    """This class validates a float"""

    def __init__(self, debug=False):
        """ Instantiates an FloatValidator object
        :param debug: bool
        :return: FloatValidator
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
            tmp_num_decimals_in_input = str(data_input)[::-1].find('.')
            if options is not None and 'fixedPrecision' in options:
                pass
            else:
                if options is not None and 'precision' in options and int(tmp_num_decimals_in_input) <= int(options['precision']):
                    tmp_input = '%.' + str(options['precision']) + 'f'
                    data_input = Decimal(tmp_input % float(data_input.replace(',', '')))
                elif tmp_num_decimals_in_input > -1:
                    data_input = Decimal(data_input.replace(',', ''))
                else:
                    data_input = Decimal(str(data_input))

            if options is not None:
                if 'max' in options and options['max'] != '' and float(options['max']) < float(data_input):
                    self.add_error(str(data_input), 'must be <= ' + str(options['max']) + '.')
                    is_valid = False

                if 'min' in options and options['min'] != '' and float(options['min']) > float(data_input):
                    self.add_error(str(data_input), 'must be >= ' + str(options['min']) + '.')
                    is_valid = False

                if 'precision' in options:
                    num_decimals_in_input = str(data_input)[::-1].find('.')
                    if int(options['precision']) != int(num_decimals_in_input):
                        self.add_error(str(data_input), 'must have ' + str(options['precision']) + ' number of decimals and input contains: ' + str(num_decimals_in_input))
                        is_valid = False
            if not is_valid:
                return False
        except Exception as e:
            self.add_error(str(e), " is not a valid float")
            return False
        return True
