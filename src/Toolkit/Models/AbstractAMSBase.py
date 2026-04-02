# @author owhoyt
import abc
import logging
import sys
import uuid

from Toolkit.Config.AMSConfig import AMSConfig
from Toolkit.Exceptions import AMSConfigException
from Toolkit.Lib.Defaults import AMSDefaults
from lib.Helpers import SASEmail


class AbstractAMSBase(object):
    __metaclass__ = abc.ABCMeta
    debug = False

    def __init__(self, ams_config):
        """
        :param ams_config:
        :type ams_config: AMSConfig
        """

        if not ams_config or not isinstance(ams_config, AMSConfig):
            raise AMSConfigException('No config passed.  AMSConfig object must be passed with a fully loaded config object.')
        self.AMSConfig = ams_config # type: AMSConfig

        self.debug = True  # @todo: pull from config file should the config file exist
        self.log_level = logging.DEBUG  # @todo: pull from config file should the config file exist
        self.AMSLogger = logging.getLogger('AMS')
        self.AMSEmail = SASEmail()
        self.AMSDefaults = AMSDefaults()
        self.AMSEmail.set_from(self.AMSDefaults.from_address)
        self.uuid = uuid.uuid4()

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

    def __str__(self):
        """magic method when you call print({myValidator}) to print the name of the validator"""
        return self.__class__.__name__

    def __del__(self):
        """This is the destructor for all validators.  Right now just placeholder"""
        return