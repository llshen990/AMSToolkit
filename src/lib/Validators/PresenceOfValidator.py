# @author owhoyt
from AbstractValidator import AbstractValidator


class PresenceOfValidator(AbstractValidator):
    """This class validates that a variable, no matter what type, is not empty or null etc."""

    def __init__(self, debug=False):
        """ Instantiates an PresenceOfValidator object
        :param debug: bool
        :return: PresenceOfValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None, include_col_name_in_error=False):
        """Validates *data_input* to ensure that it is a boolean
        :type data_input: mixed
        :param data_input: Input to validate
        :param options: field name of validation
        :param include_col_name_in_error: field name of validation
        :return: bool
        """
        try:
            if options is None:
                self.add_error('', 'PresenceOfValidator requires options parameter to be the field that is being validated')
                return False

            if not data_input or data_input is None:
                if include_col_name_in_error:
                    self.add_error(str(options), 'is a required input.')
                else:
                    self.add_error('', 'is a required input.')
                return False

            # this is to handle the data types that have a len method
            try:
                if len(data_input) == 0:
                    if include_col_name_in_error:
                        self.add_error(str(options), 'is a required input.')
                    else:
                        self.add_error('', 'is a required input.')
                    return False
            except TypeError:
                pass


        except Exception as e:
            self.add_error(str(e), 'Exception in PresenceOfValidator')
            return False
        return True
