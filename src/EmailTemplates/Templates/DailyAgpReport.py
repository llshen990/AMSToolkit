import os
import sys
from collections import OrderedDict
from datetime import datetime, timedelta
from EmailTemplates import AbstractEmailTemplate
from lib.Exceptions import EmailException, EmailSkipException
from lib.Helpers import Environments, Text2Html
from lib.AGP import AGPStatsCollection
from lib.AGP.AGPReportEmails import AGPReportEmails

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

class DailyAgpReport(AbstractEmailTemplate):
    """
    This class houses the daily AGP report functionality.
    """

    def __init__(self, debug):
        AbstractEmailTemplate.__init__(self, debug)
        self.report_mode = 'market'
        self.allowed_report_modes = [
            'market',
            'summary'
        ]

        self.allowed_report_status = [
            'success',
            'warning',
            'error'
        ]

        self.environments = Environments()

        self.txt_only_version = 'HTML-only version available'

        self.agp_stats_obj = AGPStatsCollection()

        self.report_markets = []

    def get_data(self):
        if self.market == 'SUMMARY':
            self.report_mode = 'summary'
            self.market = self.environments.my_market
        else:
            self.report_mode = 'market'

        # check to see if the report mode is allowed.
        self.is_allowed_report_mode()

        self.environments.validate_market(self.market)

        if self.report_mode == 'summary':
            self.report_markets = self.environments.all_markets
        else:
            self.report_markets = [
                self.environments.my_market
            ]

        self.agp_stats_obj.get_data_for_markets(self.report_markets, self.report_mode)
        self.data['system_status'] = self.agp_stats_obj.get_market_statuses()
        self.data['batch_data'] = self.agp_stats_obj.get_market_agp_stats()

        self._validate_data()

        return

    def _validate_data(self):
        valid_data = False
        for market, data in self.data['batch_data'].iteritems():  # type: str, dict
            if data:
                valid_data = True

        if not valid_data:
            raise EmailSkipException('No data to retrieve, not sending an email.')

    def set_body(self):

        if self.report_mode == 'summary':
            for market in self.environments.all_markets:
                system_status = 'success' if not self.check_market_status(market) else self.check_market_status(market)
                self.body += self.get_view('marketWrapper', {
                    'marketSummary': self.create_market_summary(market),
                    'marketScenarioDetails': self.create_market_details(market),
                    'systemStatus': system_status
                })

        else:
            system_status = 'success' if not self.check_market_status(self.environments.my_market) else self.check_market_status(self.environments.my_market)
            self.body += self.get_view('marketWrapper', {
                'marketSummary': self.create_market_summary(self.environments.my_market),
                'marketScenarioDetails': self.create_market_details(self.environments.my_market),
                'systemStatus': system_status
            })

        return

    def set_subject(self, data):
        if self.report_mode == "market":
            # self.subject = self.market + ' Daily AGP Report | Trx Dates: ' + ",".join(self.data['batch_data'][self.market].keys())
            self.subject = self.environments.get_market_fiendly_name(self.market) + ' Daily AGP Report | Trx Dates: '
            date_str = ""
            for run_date, agp_data in self.data['batch_data'][self.market].iteritems():
                if not agp_data['batch_started']:
                    continue
                date_str += "," if date_str else ""
                date_str += run_date
                if agp_data['waiting_for_files']:
                    break
            self.subject += date_str
        else:
            self.subject = 'Daily AGP Summary Report | ' + datetime.strftime(datetime.now(), '%Y%m%d')

        if len(self.subject) > 78:
            self.subject = self.subject[:73] + '...'

        return

    def create_market_summary(self, market):
        agp_col_header_name = 'AGP' if self.report_mode == 'market' else 'BATCH'
        summary_vars = OrderedDict()
        summary_vars['marketNameText'] = self.environments.get_market_fiendly_name(market)
        summary_vars['agp_col_header_name'] = agp_col_header_name
        if self.data['system_status'][market]['status']:
            summary_vars['systemStatusUpper'] = self.data['system_status'][market]['status'].upper()
        else:
            summary_vars['systemStatusUpper'] = 'SUCCESS'
        summary_vars['batchStatusSummaryRows'] = self.get_batch_summary_rows(market)
        summary_vars['alertSummaryRows'] = self.get_alert_summary_rows(market)

        return self.get_view('marketSummary', summary_vars)

    def get_batch_summary_rows(self, market):
        tmp_html = ''

        if market not in self.data['batch_data'] or not self.data['batch_data'][market]:
            return tmp_html

        for agp_run_date, agp_data in self.data['batch_data'][market].iteritems():
            if "batch_started" not in agp_data or not agp_data['batch_started']:
                continue
            row_vars = OrderedDict()
            row_vars['agpRunDate'] = 'N/A'
            row_vars['batchCompletionTime'] = 'N/A'
            row_vars['batchElapsedTime'] = 'N/A'

            if 'run_date_obj' in agp_data and agp_data['run_date_obj']:
                row_vars['agpRunDate'] = agp_data['run_date_obj'].strftime('%b %d, %Y')

            if self.report_mode == 'market':
                if 'agp_completed_at_obj' in agp_data and agp_data['agp_completed_at_obj']:
                    row_vars['batchCompletionTime'] = agp_data['agp_completed_at_obj'].strftime('%m/%d/%Y@%H:%M:%S') + ' ET'
            else:
                if 'completed_at_obj' in agp_data and agp_data['completed_at_obj']:
                    row_vars['batchCompletionTime'] = agp_data['completed_at_obj'].strftime('%m/%d/%Y@%H:%M:%S') + ' ET'

            if 'batch_duration' in agp_data and agp_data['batch_duration']:
                row_vars['batchElapsedTime'] = str(agp_data['batch_duration'] - timedelta(microseconds=agp_data['batch_duration'].microseconds)).strip()

            tmp_html += self.get_view('batchStatusSummaryRow', row_vars)

        return tmp_html

    def get_alert_summary_rows(self, market):

        tmp_html = ''
        tmp_alert_counts = OrderedDict()
        tmp_alert_counts['user_available_alerts'] = 0
        tmp_alert_counts['suppressed_alerts'] = 0
        tmp_alert_counts['case_assigned_closed_alerts'] = 0
        tmp_alert_counts['user_assigned_alerts'] = 0
        tmp_alert_counts['total_alerts'] = 0

        text_lookup = {
            'total_alerts': 'Total Alerts',
            'user_available_alerts': 'User Available Alerts',
            'suppressed_alerts': 'Suppressed Alerts',
            'user_assigned_alerts': 'User Assigned Alerts',
            'case_assigned_closed_alerts': 'Case Assigned / Closed Alerts'
        }

        if market not in self.data['batch_data'] or not self.data['batch_data'][market]:
            tmp_html += self.get_view('alertSummaryRow', {'alertSummaryNum': '0', 'alertSummaryText': text_lookup['user_available_alerts']})
            tmp_html += self.get_view('alertSummaryRow', {'alertSummaryNum': '0', 'alertSummaryText': text_lookup['suppressed_alerts']})
            tmp_html += self.get_view('alertSummaryRow', {'alertSummaryNum': '0', 'alertSummaryText': text_lookup['case_assigned_closed_alerts']})
            tmp_html += self.get_view('alertSummaryRow', {'alertSummaryNum': '0', 'alertSummaryText': text_lookup['user_assigned_alerts']})
            tmp_html += self.get_view('alertSummaryRow', {'alertSummaryNum': '0', 'alertSummaryText': text_lookup['total_alerts']})
            return tmp_html

        for agp_run_date, agp_data in self.data['batch_data'][market].iteritems():
            for key in tmp_alert_counts.iterkeys():
                if key == 'total_alerts':
                    continue
                tmp_alert_counts[key] += int(agp_data[key])
                tmp_alert_counts['total_alerts'] += int(agp_data[key])

        for category, alert_count in tmp_alert_counts.iteritems():
            row_vars = OrderedDict()
            row_vars['alertSummaryText'] = text_lookup[category]
            row_vars['alertSummaryNum'] = str(alert_count)
            tmp_html += self.get_view('alertSummaryRow', row_vars)

        return tmp_html

    def get_secnario_detail_rows(self, market):
        tmp_html = ''
        tmp_scenario_alert_counts = dict()

        if market not in self.data['batch_data'] or not self.data['batch_data'][market]:
            return tmp_html

        for agp_run_date, agp_data in self.data['batch_data'][market].iteritems():
            if 'scenario_alert_breakdown' not in agp_data or not agp_data['scenario_alert_breakdown']:
                continue

            for scenario_name, alert_count in agp_data['scenario_alert_breakdown'].iteritems():
                scenario_name = scenario_name.strip().upper()
                if scenario_name not in tmp_scenario_alert_counts:
                    tmp_scenario_alert_counts[scenario_name] = int(alert_count)
                else:
                    tmp_scenario_alert_counts[scenario_name] += int(alert_count)

        if tmp_scenario_alert_counts:
            for scenario_name, alert_count in OrderedDict(sorted(tmp_scenario_alert_counts.items())).iteritems():
                row_vars = dict()
                row_vars['scenarioName'] = scenario_name
                row_vars['numAlerts'] = str(alert_count)
                tmp_html += self.get_view('scenarioDetailRow', row_vars)

        return tmp_html

    def check_market_status(self, market):
        if market not in self.data['system_status']:
            self.data['system_status'][market] = {
                'status': 'warning',
                'text_msg': 'Could not determine AGP status.'
            }

        if 'status' not in self.data['system_status'][market]:
            self.data['system_status'][market]['status'] = 'warning'

            if 'text_msg' in self.data['system_status'][market]:
                self.data['system_status'][market]['text_msg'] += "<br />Unknown AGP status, setting to warning"

        if 'text_msg' not in self.data['system_status'][market]:
            self.data['system_status'][market]['text_msg'] = "Unknown AGP status, setting to warning"

        return self.data['system_status'][market]['status']

    def create_market_details(self, market):
        summary_vars = OrderedDict()
        txt2html = Text2Html(self.data['system_status'][market]['text_msg'])
        summary_vars['systemStatus'] = 'success' if not self.data['system_status'][market]['status'] else self.data['system_status'][market]['status']
        summary_vars['systemStatusText'] = txt2html.nl2br()
        summary_vars['scenarioDetailRows'] = self.get_secnario_detail_rows(market)

        return self.get_view('marketScenarioDetails', summary_vars)

    def is_allowed_report_mode(self):
        if self.report_mode not in self.allowed_report_modes:
            raise EmailException('Invalid report mode.  ' + str(self.report_mode) + ' not in ' + ', '.join(self.allowed_report_modes))

    def post_email_send_handler(self):
        for market in self.report_markets:
            if self.agp_stats_obj.agp_collection[market]:
                obj = self.agp_stats_obj.agp_collection[market]
                if self.report_mode == 'market' and len(obj.agp_run_for_dates) > 0:
                    for run_date in obj.agp_run_for_dates:
                        rpt_emails = AGPReportEmails(obj.libname, self.report_mode)
                        rpt_emails.agp_run_date = run_date
                        rpt_emails.add()
                elif self.report_mode == 'summary' and len(obj.completed_run_dates) > 0:
                    for run_date in obj.completed_run_dates:
                        rpt_emails = AGPReportEmails(obj.libname, self.report_mode)
                        rpt_emails.agp_run_date = run_date
                        rpt_emails.add()