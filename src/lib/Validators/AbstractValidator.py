# @author owhoyt
import abc

class AbstractValidator(object):
    """This is the base validator class.  It is abstract and any implemented validators should extend this class to provide
    a standardized interface for calling and using any validator.

    Attributes:
        errors: A list of errors
    """
    __metaclass__ = abc.ABCMeta
    debug = False

    def __init__(self, debug=False):
        """ Instantiates an AbstractValidator object
        :param debug: bool
        :return: AbstractValidator
        """
        self.errors = []  # creates a new empty list for holding errors
        AbstractValidator.debug = debug

    @abc.abstractmethod
    def validate(self, data_input, options=None):
        """Required method to implement a validator in order to actually validate an input

        :type data_input: mixed
        :param data_input: Input to validate
        :param options: Input options (optional) default to None.
        """
        return

    def add_error(self, data_input, error_message):
        """Adds an error message to the internal errors list in order to keep track of all errors.

        :type error_message: str
        :param data_input: value of data input that triggered error
        :param error_message: Error message
        :return bool
        """
        if self.debug:
            self.errors.append(" '" + data_input + "' " + error_message)
        else:
            self.errors.append(" " + error_message)

        return True

    def get_errors(self):
        """ This method will return the list of errors

        :return: list
        """
        return self.errors

    def format_errors(self):
        """ This method will take all errors, if any, and return a formatted string of the errors

        :return: str
        """
        if len(self.errors) == 0:
            return ""
        return "\n".join(self.errors)

    def reset_errors(self):
        """ This method will reset the error list.
        Returns: Bool
        """
        self.errors = []
        return True

    def _is_number(self, s):
        """
        This method will return bool on if the input is a number.
        :param s: mixed
        :return: bool
        """
        try:
            float(s)
            return True
        except ValueError:
            pass

        try:
            import unicodedata
            unicodedata.numeric(s)
            return True
        except (TypeError, ValueError):
            pass
        return False

    def __str__(self):
        """magic method when you call print({myValidator}) to print the name of the validator"""
        return self.__class__.__name__

    def __del__(self):
        """This is the destructor for all validators.  Right now just placeholder"""
        return