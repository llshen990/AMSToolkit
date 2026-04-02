import sys
import os
import traceback
import json

from datetime import datetime

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)


class OutputFormatHelperException(Exception):
    def __init__(self, message):
        super(OutputFormatHelperException, self).__init__(message)


class OutputFormatHelper(object):
    def __init__(self):
        pass

    @staticmethod
    def join_output_from_list(data_list, join_char=os.linesep):
        """
        This method will format a list to a string by separating each element in the list by the join_char.
        :param data_list: List of data to be formatted.
        :type data_list: list
        :param join_char: Character to use to separate each item in the list.
        :type join_char: str
        :return: Formatted string with each element separated by join_char
        :rtype: str
        """
        if not data_list:
            return ''

        if not isinstance(data_list, list):
            raise OutputFormatHelperException('Data to be output must be a list')

        try:
            output_str = ''
            for data in data_list:
                if output_str == '':
                    pass
                else:
                    output_str += join_char
                try:
                    output_str += unicode(data, encoding='ascii', errors='ignore')
                except TypeError:
                    pass
            return output_str
        except Exception as e:
            traceback.print_exc()
            return ''

    @staticmethod
    def log_msg_with_time(message):
        """
        This method will format a message prefixed with a standardized time format.
        :param message: string message to log
        :type message: str
        :return: message prefixed with standardized time
        :rtype: str
        """
        message = message.strip() + os.linesep
        return "[" + str(datetime.now().isoformat()) + "]" + message