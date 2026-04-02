import os, sys
import collections

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSAttributeMapperException, AMSAttributeMapperInfoException
from Toolkit.MetaClasses import Singleton


class AMSAttributeMapper(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.__attributes = collections.OrderedDict()

    def set_attribute(self, attribute, value, only_if_empty=False):
        """
        This method sets a key value pair in an internal memory dictionary to be retrieved at a later time.
        :param attribute: The key name.
        :type attribute: str
        :param value: The value to store.
        :param only_if_empty: Only set value in the attribute mapper if the attribute doesn't already exist.
        :type only_if_empty: bool
        :return: True upon success, Exception on error.
        :rtype: bool
        """
        if not isinstance(attribute, str):
            raise AMSAttributeMapperException('attribute in set_attribute() must be a string')

        if only_if_empty:
            try:
                self.get_attribute(attribute)
            except AMSAttributeMapperInfoException:
                self.__attributes[attribute] = value
        else:
            self.__attributes[attribute] = value

        return True

    def get_attribute(self, attribute):
        """
        This method returns the value of the desired attribute stored in memory.
        :param attribute: The string name of the value you wish to retrieve.
        :type attribute: str
        """
        if not isinstance(attribute, str):
            raise AMSAttributeMapperException('attribute in get_attribute() must be a string')

        if attribute not in self.__attributes:
            raise AMSAttributeMapperInfoException('attribute does not exist in attribute map.  Please set the attribute first via the set_attribute() method.')

        return self.__attributes[attribute]


    def is_set_attribute(self, attribute):
        """
        This method returns true if a specified attribute exists in the attribute mapper.
        :param attribute:
        :return: True
        """
        return attribute in self.__attributes

