import os, sys, collections

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSOlaException
from Toolkit.Config import AbstractAMSConfig

class AMSOla(AbstractAMSConfig):
    """
       This class defines the markets / environments
       """

    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.raw_config = collections.OrderedDict()
        self.ola_name = None  # type: str
        self.single_day = None  # type: int
        self.min_day = None  # type: int
        self.max_day = None  # type: int
        self.day_of_month = None  # type: int
        self.time_of_day = None  # type: int
        self.reset_time = None  # type: int

    def get_config_dict_key(self):
        return self.ola_name

    def get_static_config_dict_key(self):
        return 'OLA'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """
        pass

    def load(self, ola_name, config_dict):
        """
        :param ola_name: ola name from the config dict.
        :type ola_name: str
        :param config_dict: AMS config dictionary (JSON)
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            self.raw_config = config_dict
            self.ola_name = ola_name
            self._read_single_day()
            self._read_min_day()
            self._read_max_day()
            self._read_day_of_month()
            self._read_time_of_day()
            self._read_reset_time()

        except AMSOlaException:
            raise
        except Exception as e:
            raise AMSOlaException(e)

    def _read_single_day(self):
        """
        This method will set the single_day variable for the OLA.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'single_day' in self.raw_config and self.raw_config['single_day']:
            try:
                single_day_val = int(str(self.raw_config['single_day']).strip())
            except Exception as e:
                self.AMSLogger.critical('single_day requires any positive integer between 0-8: ' + str(e))
                return False

            if single_day_val < 0 or single_day_val > 8:
                self.AMSLogger.critical('single_day requires any positive integer between 0-8')
                return False

            self.single_day_val = single_day_val

        else:
            self.AMSLogger.info('single_day is not defined for the following schedule: ' + self.ola_name + '.')
            return False

        return True

    def _read_min_day(self):
        pass

    def _read_max_day(self):
        pass

    def _read_day_of_month(self):
        pass

    def _read_time_of_day(self):
        pass

    def _read_reset_time(self):
        pass

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass