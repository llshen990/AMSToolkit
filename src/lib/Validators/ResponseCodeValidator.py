# @author roward
import types
from AbstractValidator import AbstractValidator


class ResponseCodeValidator(AbstractValidator):
    """This class validates an response code"""

    def __init__(self, debug=False):
        """ Instantiates an ResponseCodeValidator object
        :param debug: bool
        :return: ResponseCodeValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is a response code

        :type data_input: mixed
        :param data_input: Input to validate
        :param options: Object of options if any are passed
        :return: bool
        """
        try:
            is_valid = True
            data_input = int(data_input)

            # We're expecting a 1XX - 5XX response code
            if not data_input in range(100, 599):
                self.add_error(str(data_input), 'must be between 100 and 599.')
                return False

            # enforce any options
            if options is not None:
                if type(options) is not types.DictionaryType:
                    is_valid = (data_input == int(options))
                else:
                    if 'max' in options and options['max'] != '' and options['max'] < data_input:
                        self.add_error(str(data_input), 'must be <= ' + str(options['max']) + '.')
                        is_valid = False

                    if 'min' in options and options['min'] != '' and options['min'] > data_input:
                        self.add_error(str(data_input), 'must be >= ' + str(options['min']) + '.')
                        is_valid = False

                    if 'range' in options and options['range'] != '':
                        code_range = options['range']
                        if len(code_range) == 3 and code_range.endswith('XX'):
                            first_digit = code_range[0]
                            if int(first_digit) in range(2, 5):
                                if data_input / 100 != int(first_digit):
                                    self.add_error(str(data_input), 'must be within range ' + str(options['range']) + '.')
                                    is_valid = False
                            else:
                                self.add_error(str(data_input), ' is not a valid range.')
                                is_valid = False
                        else:
                            self.add_error(str(data_input), ' is not a valid range.')
                            is_valid = False
            else:
                    is_valid = True

            if not is_valid:
                return False
        except Exception as e:
            self.add_error(str(e), "is not a valid response code")
            return False
        return True
