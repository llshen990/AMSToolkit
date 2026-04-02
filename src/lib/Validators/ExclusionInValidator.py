# @author owhoyt
from AbstractValidator import AbstractValidator


class ExclusionInValidator(AbstractValidator):
    """This class validates a value is not in a set"""

    def __init__(self, debug=False):
        """ Instantiates an ExclusionInValidator object
        :param debug: bool
        :return: ExclusionInValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that data is not in a set

        :type data_input: mixed
        :param data_input: Input to validate
        :param options: Data set to check if data_input exists in
        :return: bool
        """
        try:
            if options is None:
                self.add_error('N/A', 'Must pass in data set to check exclusion in.')
                return False

            is_digit = self._is_number(data_input)

            if is_digit:
                data_input = str(data_input)
            else:
                data_input = data_input.encode('UTF-8')

            if data_input in options:
                self.add_error(str(data_input), 'is in exclusion data set ' + ', '.join(options))
                return False
        except Exception as e:
            self.add_error(str(e), 'ExclusionInValidator exception')
            return False
        return True
