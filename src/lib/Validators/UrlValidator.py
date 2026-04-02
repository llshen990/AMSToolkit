# @author owhoyt
from AbstractValidator import AbstractValidator
import re

class UrlValidator(AbstractValidator):
    """This class validates a URL"""

    def __init__(self, debug=False):
        """ Instantiates an UrlValidator object
        :param debug: bool
        :return: UrlValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is a valid URL w/o checking existence.
        :type data_input: str
        :param data_input: Input to validate
        :param options: not supported for this validation type.
        :return: bool
        """
        try:
            is_digit = self._is_number(data_input)

            if is_digit:
                data_input = str(data_input)
            else:
                data_input = data_input.encode('UTF-8')

            reg_ex = re.compile(r'^(?:http|ftp)s?://'  # http:// or https://
                                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
                                r'localhost|'  # localhost...
                                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                                r'(?::\d+)?'  # optional port
                                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            if reg_ex.match(data_input):
                return True
            else:
                self.add_error(data_input, ' is not a valid URL: ' + str(options))
                return False

        except Exception as e:
            self.add_error(str(e), "Exception when validating URL")
            return False