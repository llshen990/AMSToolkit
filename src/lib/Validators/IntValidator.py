# @author owhoyt
from AbstractValidator import AbstractValidator


class IntValidator(AbstractValidator):
    """This class validates an integer"""

    def __init__(self, debug=False):
        """ Instantiates an IntValidator object
        :param debug: bool
        :return: IntValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is an integer

        :type data_input: mixed
        :param data_input: Input to validate
        :param options: Object of options if any are passed
        :return: bool
        """
        try:
            is_valid = True
            data_input = int(data_input)

            if options is not None:
                if 'max' in options and options['max'] != '' and options['max'] < data_input:
                    self.add_error(str(data_input), 'must be <= ' + str(options['max']) + '.')
                    is_valid = False

                if 'min' in options and options['min'] != '' and options['min'] > data_input:
                    self.add_error(str(data_input), 'must be >= ' + str(options['min']) + '.')
                    is_valid = False

            if not is_valid:
                return False
        except Exception as e:
            self.add_error(str(e), "is not a valid integer")
            return False
        return True
