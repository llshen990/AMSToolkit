# @author owhoyt
from AbstractValidator import AbstractValidator
import os.path


class LocaleValidator(AbstractValidator):
    """This class validates a value's locale"""

    def __init__(self, debug=False):
        """ Instantiates an LocaleValidator object
        :param debug: bool
        :return: LocaleValidator
        """
        AbstractValidator.__init__(self, debug)
        self.supported_locales_string = os.popen('locale -a').read().strip()
        self.supported_locales = self.supported_locales_string.split("\n")

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is a supported locales by SSOD
        :type data_input: str
        :param data_input: Input to validate
        :param options: not supported for this validation type.
        :return: bool
        """
        try:
            if data_input in self.supported_locales:
                return True
            else:
                self.add_error(str(data_input), "is not a supported locale: " + ", ".join(self.supported_locales))
            return False
        except Exception as e:
            self.add_error(str(e), 'Caught exception validating locale')
            return False
