import os
import sys
import re
import json
from datetime import datetime
from collections import OrderedDict

from PythonSASConnector import AbstractPythonSASConnector

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

class ScenarioAlertStats(AbstractPythonSASConnector):
    """
    This class houses information about Scenario Alert Stats
    """

    def __init__(self, libname):
        AbstractPythonSASConnector.__init__(self)
        self.libname = libname
        self.scenario_name = None
        self.alert_count = 0

    def map_fields(self):
        self.field_map = [
            'scenario_name',
            'alert_count'
        ]

        return True

    def class_instantiation_args(self):
        return [self.libname]

    def get_scenario_alert_breakdown(self, start_date_obj, end_date_obj):
        """
        This method will get the number of alerts .
        :param start_date_obj: Begin Date Object
        :type start_date_obj: datetime
        :param end_date_obj: End Date Object
        :type end_date_obj: datetime
        :return: List of loaded ScenarioAlertStats objects
        :rtype: list[ScenarioAlertStats]
        """
        sql = """
            SELECT
                SCENARIO_NAME,
                count(*) as alert_count
            FROM
                {libname}.RPT_ALERT_DIM
            WHERE
                CREATE_DATE between {start_date}dt AND {end_date}dt
            GROUP BY
                SCENARIO_NAME
        """.format(
            libname=self.libname,
            start_date=self._escape_var(start_date_obj.strftime('%d%b%Y:%H:%M:%S')),
            end_date=self._escape_var(end_date_obj.strftime('%d%b%Y:%H:%M:%S'))
        )

        self.exec_query(sql)
        breakdown = self._load_all_results() # type: list[ScenarioAlertStats]
        # breakdown = self._load_all_results('/tmp/scenario_alert_breakdown.out') # type: list[ScenarioAlertStats]

        ret_list = {}
        for scenario_alert_stat in breakdown:
            ret_list[scenario_alert_stat.scenario_name] = scenario_alert_stat.alert_count

        return ret_list