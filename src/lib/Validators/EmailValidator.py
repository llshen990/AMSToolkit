# @author owhoyt
from AbstractValidator import AbstractValidator
from email.utils import parseaddr

import re


class EmailValidator(AbstractValidator):
    """This class validates a syntactically correct email"""

    def __init__(self, debug=False):
        """ Instantiates an EmailValidator object
        :param debug: bool
        :return: EmailValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is an integer

        :type data_input: mixed
        :param data_input: Input to validate
        :param options: None implemented for this validator
        :return: bool
        """
        try:
            parsed_address = parseaddr(data_input)
            if not parsed_address[1]:
                self.add_error(str(data_input), " is not a valid email")
                return False

            reg_ex = re.compile("(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")
            if not reg_ex.match(parsed_address[1]):
                self.add_error(str(data_input), " is not a valid email format")
                return False
        except Exception as e:
            self.add_error(str(data_input) + ": " + str(e), " failed validation")
            return False
        return True

    def validate_email_list(self, data_input, allow_empty=False):
        """
        This method will validate *data_input* as a list of email addresses.
        :param data_input: str
        :param allow_empty: bool
        :return: str
        """
        data_input = data_input.strip()
        # if the string is empty, return an empty string.
        if not data_input and not allow_empty:
            self.add_error(str(data_input), " cannot be empty")
            return False
        elif not data_input and allow_empty:
            return ''

        deliminator = ''
        if data_input.find(','):
            deliminator = ','
        elif data_input.find(';'):
            deliminator = ';'
        elif data_input.find(' '):
            deliminator = ' '

        if not deliminator:
            if self.validate(data_input):
                return data_input
            else:
                return False
        else:
            email_list = data_input.split(deliminator)
            for email_address in email_list:
                self.validate(email_address)

            if self.get_errors():
                return False
            else:
                return ','.join([str(i) for i in email_list])
