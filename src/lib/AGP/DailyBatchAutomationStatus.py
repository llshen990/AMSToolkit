import os
import sys
import re
import json
from datetime import datetime
from collections import OrderedDict

from lib.Exceptions import DailyBatchAutomationStatusException
from PythonSASConnector import AbstractPythonSASConnector
from lib.Helpers import Environments

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)


class DailyBatchAutomationStatus(AbstractPythonSASConnector):
    """
    This class houses information about AGP Status
    """

    def __init__(self, libname):
        AbstractPythonSASConnector.__init__(self)
        self.market = None
        self.status = None
        self.text_msg = None

        self.allowed_statuses = [
            'success',
            'warning',
            'error'
        ]

        self.id = None
        self.batch_group = None
        self.batch_cycle_name = None
        self.agp_run_date = None
        self.created_date = None
        self.created_date_obj = None
        self.sys_user = None
        self.info = None
        self.status = None
        self.flg_deleted = None

        self.libname = libname
        self.table = 'daily_batch_automation_status'
        self.primary_key_field = 'id'

        self.environment = Environments()

    def map_fields(self):
        self.field_map = [
            'id',
            'batch_group',
            'batch_cycle_name',
            'agp_run_date',
            'created_date',
            'sys_user',
            'info',
            'status',
            'flg_deleted'
        ]

        return True

    def class_instantiation_args(self):
        return [self.libname]

    def get_create_date_obj(self):
        if not self.created_date:
            return None
        return datetime.strptime(self.created_date, '%d%b%Y:%H:%M:%S.%f')

    def get_friendly_status(self, current_status_text, cur_run_date=None):
        if not self.status:
            return 'Unknown status'

        extra_info = ''
        ssod_str = 'SAS Solutions OnDemand'

        if self.status == 'START':
            suffix = 'has started.'
        elif self.status == 'ERROR':
            suffix = 'has encountered an error.  The ' + ssod_str + ' on-call team is investigating.'
        elif self.status == 'COMPLETE':
            suffix = 'has completed successfully.'
        elif self.status == 'TOO_MANY_FILES':
            return 'Batch is on hold due to multiple files received for the same transaction date for the same data source.  Please refer to the missing file reports for more details.'
        elif self.status == 'TOO_MANY_MANIFESTS':
            return 'Batch is on hold due to multiple manifests received for the same transaction date for the same data source.  Please refer to the missing file reports for more details.'
        elif self.status == 'DQ_ERROR':
            return 'Batch is on hold due to a Data Quality error on one or more of the source files.  Please refer to JIRA and/or technical emails for more details.'
        elif self.status == 'ONE_AND_STOP':
            return current_status_text
        elif self.status == 'TEMP_STOP_ON_TWMNT':
            return current_status_text
        elif self.status == 'TEMP_STOP_ON':
            return current_status_text
        elif self.status == 'TEMP_STOP_OFF':
            return current_status_text
        elif self.status == 'DUPLICATE_CHECK':
            return 'The duplicate check is currently running.'
        elif self.status == 'DUPLICATE_CHECK_ERROR':
            return 'There has been an error running the duplicate check.  Please contact your SAS Solutions OnDemand team for further details.'
        elif self.status == 'MISSING_MANIFEST':
            return 'Batch is on hold due to missing manifests required for the batch.  Please refer to the missing file reports for more details.'
        elif self.status == 'MISSING_FILE':
            if cur_run_date:
                optimal_run_date = int(self.environment.get_optimal_run_date(self.environment.my_market))
                if optimal_run_date > int(cur_run_date):
                    return 'Batch is on hold due to missing files required for the batch.  Please refer to the missing file reports for more details.'
                else:
                    return 'The daily AGP batch process is waiting for the next set of files to arrive.'
            else:
                return 'Batch is on hold due to missing files required for the batch.  Please refer to the missing file reports for more details.'
        else:
            suffix = 'is an unknown state.  Please contact the ' + ssod_str + ' for further questions'

        batch_friendly_name = 'Unknown process name'
        if self.batch_cycle_name == 'dailycycle_010_batchinit':
            batch_friendly_name = 'Batch Init'
            extra_info = "  SAS is currently waiting on the next complete set of files to arrive for transaction date " + self.agp_run_date
        elif self.batch_cycle_name == 'dailycycle_020_maniland':
            batch_friendly_name = 'Extract'
        elif self.batch_cycle_name == 'dailycycle_030_er':
            batch_friendly_name = 'Entity Resolution'
        elif self.batch_cycle_name == 'dailycycle_040_datamgt':
            batch_friendly_name = 'Data Management (Extract to Stage, Stage to Core, AGP)'
        elif self.batch_cycle_name == 'dailycycle_050_vaload':
            batch_friendly_name = 'Visual Analytics'
        elif self.batch_cycle_name == 'dailycycle_060_solr':
            batch_friendly_name = 'SOLR'
        elif self.batch_cycle_name == 'dailycycle_065_oracle_stats':
            batch_friendly_name = 'Oracle Stats Optimization'
        elif self.batch_cycle_name == 'dailycycle_070_batchterm':
            batch_friendly_name = 'Batch Finalization'

        return 'The ' + batch_friendly_name + ' process ' + suffix + extra_info
