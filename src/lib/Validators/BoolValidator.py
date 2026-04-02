# @author owhoyt
from AbstractValidator import AbstractValidator

import types


class BoolValidator(AbstractValidator):
    """This class validates a boolean"""

    def __init__(self, debug=False):
        """ Instantiates an BoolValidator object
        :param debug: bool
        :return: BoolValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is a boolean
        :type data_input: bool
        :param data_input: Input to validate
        :param options: not implemented in this validator
        :return: bool
        """
        try:
            if type(data_input) != types.BooleanType:
                raise ValueError()
        except Exception as e:
            self.add_error(str(e), "is not a valid boolean")
            return False
        return True
