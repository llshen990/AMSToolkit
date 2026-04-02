# @author owhoyt
from AbstractValidator import AbstractValidator

class StrValidator(AbstractValidator):
    """This class validates a string"""

    def __init__(self, debug=False):
        """ Instantiates an StrValidator object
        :param debug: bool
        :return: StrValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is a string

        :type data_input: mixed
        :param data_input: Input to validate
        :param options: Object of options if any are passed
        :return: bool
        """
        try:
            is_valid = True
            is_digit = self._is_number(data_input)

            if is_digit:
                data_input = str(data_input)
                string_length = len(data_input)
            else:
                data_input = data_input.encode('UTF-8')
                string_length = len(data_input.decode('UTF-8'))

            if options is not None:
                if ('allowDigit' not in options and is_digit) or ('allowDigit' in options and not options['allowDigit'] and is_digit):
                    self.add_error(data_input, 'is expecting a string, digit given.')
                    return False

                if 'max' in options and options['max'] != '' and options['max'] < string_length:
                    self.add_error(data_input, 'must be <= ' + str(options['max']) + ' characters in length.')
                    is_valid = False

                if 'min' in options and options['min'] != '' and options['min'] > string_length:
                    self.add_error(data_input, 'must be >= ' + str(options['min']) + ' characters in length.')
                    is_valid = False

            if not is_valid:
                return False
        except Exception as e:
            self.add_error(str(e), " is not a valid string")
            return False
        return True