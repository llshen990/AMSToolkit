import os
import sys
import re
import json
from datetime import datetime
from collections import OrderedDict

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from lib.Helpers import Environments
from lib.Exceptions import AGPStatsException
from PythonSASConnector import AbstractPythonSASConnector

class AGPStats(AbstractPythonSASConnector):
    """
    This class houses information about AGP Statistics
    """

    def __init__(self, libname):
        AbstractPythonSASConnector.__init__(self)
        self.libname = libname
        self.user_available_alerts = 0
        self.suppressed_alerts = 0
        self.case_assigned_closed_alerts = 0
        self.user_assigned_alerts = 0
        self.total_alerts = 0

    def map_fields(self):
        self.field_map = [
            'total_alerts',
            'suppressed_alerts',
            'user_available_alerts',
            'user_assigned_alerts',
            'case_assigned_closed_alerts'
        ]

        return True

    def class_instantiation_args(self):
        return [self.libname]

    def get_num_alerts(self, start_date_obj, end_date_obj):
        """
        This method will get the alert counts between two dates.
        :param start_date_obj: Begin Date Object
        :type start_date_obj: datetime
        :param end_date_obj: End Date Object
        :type end_date_obj: datetime
        :return: True upon success
        :rtype: bool
        """
        sql = """
            SELECT
                    count(*) as totalAlerts,
                    (select count(*) from {libname}.rpt_incident WHERE incident_disposition_cd = 'SUE' AND CREATE_DTTM between {start_date}dt AND {end_date}dt) as suppressedAlerts ,
                    (select count(*) from {libname}.rpt_incident WHERE investigator_user_id is null AND (incident_disposition_cd = 'ACT' OR incident_disposition_cd is null) AND case_rk is null AND CREATE_DTTM between {start_date}dt AND {end_date}dt) as userAvailableAlerts,
                    (select count(*) from {libname}.rpt_incident WHERE investigator_user_id is not null AND (incident_disposition_cd = 'ACT' ) AND CREATE_DTTM between {start_date}dt AND {end_date}dt) as userAssigned,
                    (select count(*) from {libname}.rpt_incident WHERE (case_rk IS NOT NULL or incident_disposition_cd = 'CLS') AND CREATE_DTTM between {start_date}dt AND {end_date}dt) as caseAssigned
            FROM
                    {libname}.rpt_incident
            WHERE
                    CREATE_DTTM between {start_date}dt AND {end_date}dt
        """.format(
            libname=self.libname,
            start_date=self._escape_var(start_date_obj.strftime('%d%b%Y:%H:%M:%S')),
            end_date=self._escape_var(end_date_obj.strftime('%d%b%Y:%H:%M:%S'))
        )

        self.exec_query(sql)
        self._load_single_result()
        # self._load_single_result('/tmp/agp_stats.out')
