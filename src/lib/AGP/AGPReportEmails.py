import os
import sys
import re
import json
from datetime import datetime
from collections import OrderedDict

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from lib.Helpers import Environments
from lib.AGP import ScenarioAlertStats
from lib.Exceptions import AGPReportEmailsException
from PythonSASConnector import AbstractPythonSASConnector


class AGPReportEmails(AbstractPythonSASConnector):
    """
    This class houses information about AGP Emails
    """

    def __init__(self, libname, report_mode):
        AbstractPythonSASConnector.__init__(self)
        self.libname = libname
        self.agp_run_date = None
        # report mode is expected to be validated prior to using this class
        self.report_mode = report_mode
        self.table = 'agp_report_emails'

    def map_fields(self):
        self.field_map = [
            'agp_run_date',
            'report_mode'
        ]

        return True

    def class_instantiation_args(self):
        return [self.libname]

    def get_max_rudate_for_report_type(self):
        """
        This method will get the alert counts between two dates.
        :return: Date in integer form
        :rtype: int
        """
        try:
            sql = """
                SELECT
                    MAX(agp_run_date) as max_agp_run_date,
                    report_type
                FROM
                    {libname}.{table}
                WHERE
                    report_type = {report_type}
            """.format(
                libname=self.libname,
                table=self.table,
                report_type=self._escape_var(self.report_mode)
            )

            self.exec_query(sql)
            self._load_single_result()

            if not self.agp_run_date:
                return 0

            return self.agp_run_date

        except Exception as e:
            raise AGPReportEmailsException(e)
