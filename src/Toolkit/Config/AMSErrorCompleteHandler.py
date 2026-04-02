import sys
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSCompleteHandler

class AMSErrorCompleteHandler(AMSCompleteHandler):
    """
    This class defines the error/success handlers
    """

    def __init__(self):
        AMSCompleteHandler.__init__(self)

    def get_static_config_dict_key(self, value=None):
        return 'error_complete_handler'

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass