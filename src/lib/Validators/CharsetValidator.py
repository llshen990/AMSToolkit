# @author owhoyt
from AbstractValidator import AbstractValidator
import os.path


class CharsetValidator(AbstractValidator):
    """This class validates a value's charset"""

    def __init__(self, debug=False):
        """ Instantiates an CharsetValidator object
        :param debug: bool
        :return: CharsetValidator
        """
        AbstractValidator.__init__(self, debug)
        self.supported_charsets_string = os.popen('iconv -l').read()
        self.supported_charsets = self.supported_charsets_string.lower().split("//\n")

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is a supported charset by SSOD
        :type data_input: str
        :param data_input: Input to validate
        :param options: not supported for this validation type.
        :return: bool
        """
        data_input = data_input.lower()
        if data_input in self.supported_charsets:
            return True
        else:
            self.add_error(str(data_input), "is not a supported charset: " + ", ".join(self.supported_charsets))
        return False
