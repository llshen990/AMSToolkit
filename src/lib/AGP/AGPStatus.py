import os
import sys
from datetime import datetime, timedelta
from collections import OrderedDict
# import json

from DailyBatchAutomationStatus import DailyBatchAutomationStatus
from lib.Helpers import Environments
from ScenarioAlertStats import ScenarioAlertStats
from AGPStats import AGPStats

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)


class AGPStatus(object):
    """
    This class houses information about AGP Status
    """

    def __init__(self, market, report_mode):
        self.environment = Environments()
        self.environment.validate_market(market)
        self.market = market
        self.overall_status = None
        self.overall_status_text = ''
        self.tmp_stop_message = None
        self.daily_batch_automation_status_list = []  # type: List[DailyBatchAutomationStatus]
        self.agp_batch_status = OrderedDict()

        self.last_job_name_friendly = None
        self.last_job_name = None
        self.last_status = None
        self.batch_started = False
        self.batch_completed = False
        self.batch_error = False
        self.temp_stop = False
        self.full_batch_zero_alerts = False
        self.zero_alert_run_dates = []
        self.current_run_date = 0
        self.waiting_for_files = True
        # report mode is expected to be validated prior to using this class
        self.report_mode = report_mode
        self.agp_run_for_dates = []
        self.completed_run_dates = []
        self.agp_completed = False
        self.allowed_zero_alerts_success = [
            'WZA'
        ]

        self.market_to_libname_map = {
            'WMX': 'fcs_rpt',
            'WPN': 'rpt_cam',
            'WCA': 'rpt_can',
            'WCL': 'rpt_wcl',
            'WZA': 'rpt_wza',
            'WBR': 'rpt_wbr',
            'WIN': 'rpt_win',
            'WUK': 'rpt_wuk'
        }

        self.libname = self.market_to_libname_map[self.market.upper()]

        self.agp_stats = AGPStats(self.libname)

        self.allowed_statuses = [
            'success',
            'warning',
            'error'
        ]

        self.batch_start_jobs = [
            'dailycycle_010_batchinit'
        ]

        self.batch_finish_jobs = [
            'dailycycle_070_batchterm'
        ]

        self.batch_jobs_all_files_received = {
            'dailycycle_020_maniland': [
                "START"
            ],
            'dailycycle_030_er': [
                "START",
                "COMPLETE",
            ],
            'dailycycle_040_datamgt': [
                "START",
                "COMPLETE",
            ],
            'dailycycle_050_vaload': [
                "START",
                "COMPLETE",
            ],
            'dailycycle_060_solr': [
                "START",
                "COMPLETE",
            ],
            'dailycycle_065_oracle_stats': [
                "START",
                "COMPLETE",
            ],
            'dailycycle_070_batchterm': [
                "START",
                "COMPLETE",
            ],
        }

        self.available_batch_job_names = [
            'dailycycle_010_batchinit',
            'dailycycle_020_maniland',
            'dailycycle_030_er',
            'dailycycle_040_datamgt',
            'dailycycle_050_vaload',
            'dailycycle_060_solr',
            'dailycycle_065_oracle_stats',
            'dailycycle_070_batchterm'
        ]

        self.completed_run_dates = []

        self.status_not_run_date_specific_list = [
            "TEMP_STOP_OFF",
            "TEMP_STOP_ON",
            "TEMP_STOP_ON_TWMNT",
            "ONE_AND_STOP"
        ]

    def get_status(self):
        dba_obj = DailyBatchAutomationStatus(self.libname)

        self.daily_batch_automation_status_list = dba_obj.filter_object({
            'where_equal': {
                'flg_deleted': 0,
                'batch_group': 'DAILY_CYCLE'
            },
            'where': [
                'agp_run_date IS NOT NULL',
                "agp_run_date > (SELECT (CASE WHEN MAX(agp_run_date) IS NULL THEN 0 ELSE MAX(agp_run_date) END) FROM " + self.market_to_libname_map[self.market] + ".agp_report_emails WHERE report_mode = '" + self.report_mode + "')"
            ],
            'order': {
                'agp_run_date': 'ASC',
                'created_date': 'ASC'
            }
        })  # type: List[DailyBatchAutomationStatus]

        status_grouping = OrderedDict()
        run_dt = None
        for cls in self.daily_batch_automation_status_list:
            if run_dt != cls.agp_run_date:
                run_dt = cls.agp_run_date
                status_grouping[run_dt] = OrderedDict()

            self.determine_current_batch_status(cls)

        # self.duration = str(self.agp_batch_status['batch_duration']

        if self.batch_error:
            self.overall_status = 'error'
        elif self.tmp_stop_message and self.overall_status == 'success':
            self.overall_status = 'warning'

        if self.full_batch_zero_alerts and self.market not in self.allowed_zero_alerts_success:
            if self.overall_status != 'error':
                self.overall_status = 'warning'
            self.overall_status_text += os.linesep + os.linesep + 'Batch has completed and generated zero alerts for the the following run dates: ' + ','.join(self.zero_alert_run_dates) + ".  Please investigate if this is expected or if investigation is necessary by the SAS Solutions OnDemand team."

        if self.batch_started and not self.batch_completed and not self.batch_error and not self.waiting_for_files and self.report_mode != 'market':
            # self.overall_status = 'warning'
            self.overall_status_text += os.linesep + os.linesep + 'Batch is still processing and will continue during the next batch window'
            if self.overall_status == 'error':
                self.overall_status_text += ' after the error is resolved.'
            else:
                self.overall_status_text += '.'
        elif self.report_mode == 'market' and self.agp_completed:
            self.overall_status_text += os.linesep + os.linesep + 'The Enterprise Case Management UI is ready for use.'

        if self.tmp_stop_message:
            self.overall_status_text += os.linesep + os.linesep + self.tmp_stop_message

            # print json.dumps(self.agp_batch_status, indent=4, default=str)
            # exit()

    def determine_current_batch_status(self, dba_obj):
        """
        :param dba_obj: Loaded daily job status object.
        :type dba_obj: DailyBatchAutomationStatus
        :return: True upon success
        :rtype: bool
        """
        if dba_obj.agp_run_date not in self.agp_batch_status:
            self.init_job_status(dba_obj.agp_run_date)

        if dba_obj.batch_cycle_name in self.batch_start_jobs and dba_obj.status == 'START':
            self.batch_started = True
            self.batch_completed = False
            self.agp_batch_status[dba_obj.agp_run_date]['batch_started'] = True
            self.agp_batch_status[dba_obj.agp_run_date]['started_at'] = dba_obj.get_create_date_obj()
            self.current_run_date = int(dba_obj.agp_run_date)
        elif dba_obj.batch_cycle_name in self.batch_finish_jobs and dba_obj.status == 'COMPLETE':
            self.batch_completed = True
            self.agp_batch_status[dba_obj.agp_run_date]['batch_completed'] = True
            self.agp_batch_status[dba_obj.agp_run_date]['completed_at_obj'] = dba_obj.get_create_date_obj()
            if dba_obj.agp_run_date not in self.completed_run_dates:
                self.completed_run_dates.append(dba_obj.agp_run_date)

        if dba_obj.batch_cycle_name in self.available_batch_job_names:
            if not dba_obj.batch_cycle_name in self.agp_batch_status[dba_obj.agp_run_date]['jobs']:
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name] = {
                    'started': False,
                    'completed': False,
                    'is_error': False,
                    'is_temp_stop': False,
                    'last_start_date_obj': None,
                    'last_complete_date_obj': None,
                    'last_error_date_obj': None,
                    'last_temp_stop_date_obj': None
                }

            if dba_obj.batch_cycle_name in self.batch_jobs_all_files_received and dba_obj.status in self.batch_jobs_all_files_received[dba_obj.batch_cycle_name]:
                self.agp_batch_status[dba_obj.agp_run_date]['waiting_for_files'] = False
                self.waiting_for_files = False
            else:
                self.agp_batch_status[dba_obj.agp_run_date]['waiting_for_files'] = True
                self.waiting_for_files = True

            if dba_obj.status == 'START':
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['started'] = True
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['completed'] = False
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['is_error'] = False
                self.agp_batch_status[dba_obj.agp_run_date]['batch_error'] = False
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['last_start_date_obj'] = dba_obj.get_create_date_obj()
                self.batch_error = False
            elif dba_obj.status == 'COMPLETE':
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['completed'] = True
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['is_error'] = False
                self.agp_batch_status[dba_obj.agp_run_date]['batch_error'] = False
                if dba_obj.get_create_date_obj() and self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['last_start_date_obj']:
                    self.agp_batch_status[dba_obj.agp_run_date]['batch_duration'] += (dba_obj.get_create_date_obj() - self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['last_start_date_obj'])
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['last_complete_date_obj'] = dba_obj.get_create_date_obj()

                if dba_obj.batch_cycle_name == 'dailycycle_040_datamgt':
                    start_date_tmp = self.agp_batch_status[dba_obj.agp_run_date]['started_at'] if self.agp_batch_status[dba_obj.agp_run_date]['started_at'] else self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['last_start_date_obj']
                    self.agp_stats.get_num_alerts(start_date_tmp, dba_obj.get_create_date_obj())
                    scenario_alert_stats = ScenarioAlertStats(self.libname)
                    self.agp_batch_status[dba_obj.agp_run_date]['scenario_alert_breakdown'] = scenario_alert_stats.get_scenario_alert_breakdown(start_date_tmp, dba_obj.get_create_date_obj())
                    self.agp_batch_status[dba_obj.agp_run_date]['total_alerts'] = self.agp_stats.total_alerts
                    self.agp_batch_status[dba_obj.agp_run_date]['user_available_alerts'] = self.agp_stats.user_available_alerts
                    self.agp_batch_status[dba_obj.agp_run_date]['suppressed_alerts'] = self.agp_stats.suppressed_alerts
                    self.agp_batch_status[dba_obj.agp_run_date]['case_assigned_closed_alerts'] = self.agp_stats.case_assigned_closed_alerts
                    self.agp_batch_status[dba_obj.agp_run_date]['user_assigned_alerts'] = self.agp_stats.user_assigned_alerts
                    if int(self.agp_stats.total_alerts) == 0:
                        self.full_batch_zero_alerts = True
                        self.zero_alert_run_dates.append(dba_obj.agp_run_date)

                    if dba_obj.agp_run_date not in self.agp_run_for_dates:
                        self.agp_run_for_dates.append(dba_obj.agp_run_date)

                    self.agp_batch_status[dba_obj.agp_run_date]['agp_completed'] = True
                    self.agp_batch_status[dba_obj.agp_run_date]['agp_completed_at_obj'] = dba_obj.get_create_date_obj()

                    if self.report_mode == 'market':
                        self.agp_completed = True

                self.batch_error = False
            elif dba_obj.status == 'ERROR':
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['completed'] = False
                self.agp_batch_status[dba_obj.agp_run_date]['batch_error'] = True
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['is_error'] = True
                if dba_obj.get_create_date_obj() and self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['last_start_date_obj']:
                    self.agp_batch_status[dba_obj.agp_run_date]['batch_duration'] += (dba_obj.get_create_date_obj() - self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['last_start_date_obj'])
                self.agp_batch_status[dba_obj.agp_run_date]['jobs'][dba_obj.batch_cycle_name]['last_error_date_obj'] = dba_obj.get_create_date_obj()
                self.batch_error = True

            self.temp_stop = False

        self.agp_batch_status[dba_obj.agp_run_date]['last_status'] = dba_obj.status
        self.agp_batch_status[dba_obj.agp_run_date]['last_job_name'] = dba_obj.batch_cycle_name
        self.agp_batch_status[dba_obj.agp_run_date]['last_job_name_friendly'] = dba_obj.batch_cycle_name

        self._determine_overall_status(dba_obj)

        return True

    def _determine_overall_status(self, dba_obj):
        """
        :param dba_obj: Loaded daily job status object.
        :type dba_obj: DailyBatchAutomationStatus
        :return: True upon success
        :rtype: bool
        """

        if not self.current_run_date:
            self.current_run_date = dba_obj.agp_run_date

        if self.current_run_date < int(dba_obj.agp_run_date) and dba_obj.status not in self.status_not_run_date_specific_list:
            return False

        self.overall_status = 'success'
        self.overall_status_text = dba_obj.get_friendly_status(self.overall_status_text, int(dba_obj.agp_run_date))

        if dba_obj.status == 'TEMP_STOP_ON':
            self.tmp_stop_message = 'The manual stop has been placed on this batch.  Please contact your SAS Solutions OnDemand team for further details.'
            self.temp_stop = True
        elif dba_obj.status == 'TEMP_STOP_ON_TWMNT':
            self.overall_status = 'warning'
            self.temp_stop = True
            self.tmp_stop_message = 'The manual stop has been placed on this batch while SAS is conducting a scheduled maintenance.  The batch will resume upon maintenance completion.'
        elif dba_obj.status == 'TOO_MANY_FILES':
            self.overall_status = 'error'
            self.batch_error = True
        elif dba_obj.status == 'TOO_MANY_MANIFESTS':
            self.overall_status = 'error'
            self.batch_error = True
        elif dba_obj.status == 'DQ_ERROR':
            self.overall_status = 'error'
            self.batch_error = True
        elif dba_obj.status == 'ONE_AND_STOP':
            self.tmp_stop_message = 'The manual stop has been placed on this batch after running one complete batch cycle.  This allowed the automation to run one full cycle and then stop before processing any further batches.  Please contact your SAS Solutions OnDemand team for further details.'
            self.temp_stop = True
        elif dba_obj.status == 'DUPLICATE_CHECK':
            self.overall_status = 'success'
        elif dba_obj.status == 'DUPLICATE_CHECK_ERROR':
            self.overall_status = 'error'
            self.batch_error = True
        elif dba_obj.status == 'MISSING_MANIFEST':
            self.overall_status = 'error'
            self.batch_error = True
        elif dba_obj.status == 'MISSING_FILE':
            optimal_run_date = int(self.environment.get_optimal_run_date(self.environment.my_market))
            # only want to set this to an error if we're behind on run-date.
            if optimal_run_date > int(dba_obj.agp_run_date):
                self.overall_status = 'error'
                self.batch_error = True
        elif dba_obj.status == 'TEMP_STOP_OFF' and self.tmp_stop_message:
            self.tmp_stop_message = ''
            self.temp_stop = False
        return True

    def init_job_status(self, run_date):
        self.agp_batch_status[run_date] = {
            'run_date_obj': datetime.strptime(run_date, '%Y%m%d'),
            'batch_started': False,
            'batch_error': False,
            'batch_completed': False,
            'agp_completed': False,
            'batch_duration': timedelta(),
            'started_at': None,
            'completed_at_obj': None,
            'agp_completed_at_obj': None,
            'jobs': OrderedDict(),
            'last_status': None,
            'last_job_name': None,
            'user_available_alerts': 0,
            'suppressed_alerts': 0,
            'case_assigned_closed_alerts': 0,
            'user_assigned_alerts': 0,
            'total_alerts': 0,
            'waiting_for_files': True,
            'scenario_alert_breakdown': {

            }
        }

    def get_max_rundate_for_type(self):
        pass

    def get_agp_stats(self):
        return self.agp_batch_status

    def get_agp_report_status(self):
        return self.overall_status

    def get_agp_report_text(self):
        return self.overall_status_text
