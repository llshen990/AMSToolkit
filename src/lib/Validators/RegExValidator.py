# @author owhoyt
from AbstractValidator import AbstractValidator
import re


class RegExValidator(AbstractValidator):
    """This class validates a regex"""

    def __init__(self, debug=False):
        """ Instantiates an RegExValidator object
        :param debug: bool
        :return: RegExValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None, regex_flags=0):
        """Validates *data_input* to ensure that it matches a regex

        :type data_input: mixed
        :param data_input: Input to validate
        :param options: none should be passed
        :param regex_flags: 0 or flags for regex
        :return: bool
        """
        try:
            if options is None:
                self.add_error('', 'Must pass regex pattern.')
                return False

            is_digit = self._is_number(data_input)

            if is_digit:
                data_input = str(data_input)
            # else:
            #     data_input = data_input.encode('UTF-8')

            reg_ex = re.compile(options, regex_flags)
            if reg_ex.match(data_input):
                return True
            else:
                self.add_error(data_input, 'did not match pattern: ' + str(options))
                return False

        except Exception as e:
            self.add_error(str(e), "Exception when validating RegEx")
            return False
