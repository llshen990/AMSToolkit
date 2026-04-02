# @author owhoyt
from AbstractValidator import AbstractValidator


class AlphaValidator(AbstractValidator):
    """This class validates an alpha"""

    def __init__(self, debug=False):
        """ Instantiates an AlphaValidator object
        :param debug: bool
        :return: AlphaValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is an alpha value

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
            else:
                data_input = data_input.encode('UTF-8')

            if not data_input.isalpha():
                self.add_error(data_input, 'is expecting an alpha, invalid characters given.')
                return False

            if options is not None:
                if 'max' in options and options['max'] != '' and options['max'] < len(data_input):
                    self.add_error(data_input, 'must be <= ' + str(options['max']) + ' characters in length.')
                    is_valid = False

                if 'min' in options and options['min'] != '' and options['min'] > len(data_input):
                    self.add_error(data_input, 'must be >= ' + str(options['min']) + ' characters in length.')
                    is_valid = False

            if not is_valid:
                return False
        except Exception as e:
            self.add_error(str(e), "is not a valid alpha")
            return False
        return True
