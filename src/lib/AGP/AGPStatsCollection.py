import os
import sys
import re
import json
from datetime import datetime
from collections import OrderedDict

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from lib.Helpers import Environments
from lib.Exceptions import AGPStatsCollectionException
from lib.AGP.AGPStatus import AGPStatus

class AGPStatsCollection(object):
    """
    This class houses a collection of multiple AGPStats classes
    """

    def __init__(self):
        self.agp_collection = OrderedDict()
        self.environments = Environments()
        self.__data_loaded = False
        # report_mode mode is expected to be validated prior to using this class
        self.report_mode = None

    def get_data_for_markets(self, markets, report_mode):
        # report mode is expected to be validated prior to using this class
        self.report_mode = report_mode

        if not markets or len(markets) < 1:
            raise AGPStatsCollectionException('At least one market required in a list.')

        for market in markets:
            self.environments.validate_market(market)
            agp_status = AGPStatus(market, self.report_mode)
            agp_status.get_status()
            # agp_status.get_stats()
            self.agp_collection[market] = agp_status

        self.__data_loaded = True

    def get_market_statuses(self):
        if not self.__data_loaded:
            raise AGPStatsCollectionException('Must call get_data_for_markets() prior to get_market_statuses()')

        ret_dict = {}
        #
        for market, agp_status in self.agp_collection.iteritems():  # type:str,AGPStatus
            ret_dict[market] = {
                'status': agp_status.get_agp_report_status(),
                'text_msg': agp_status.get_agp_report_text()
            }

        # print json.dumps(ret_dict, indent=4)

        return ret_dict

    def get_market_agp_stats(self):
        if not self.__data_loaded:
            raise AGPStatsCollectionException('Must call get_data_for_markets() prior to get_market_statuses()')

        ret_dict = {}

        for market, agp_status in self.agp_collection.iteritems():  # type:str,AGPStatus
            ret_dict[market] = agp_status.get_agp_stats()

        return ret_dict