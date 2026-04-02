import os
import sys
import re
import json
from datetime import datetime
from collections import OrderedDict
import traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from EmailTemplates import AbstractEmailTemplate
from lib.Validators import FileExistsValidator, IntValidator
from lib.Exceptions import EmailException
from lib.Helpers import SASEmail, UpdateBatchStatus, Environments


class MissingFileReport(AbstractEmailTemplate):
    """
    This class houses the missing file report functionality.
    """

    def __init__(self, debug):
        AbstractEmailTemplate.__init__(self, debug)
        self.data_source = '/tmp/file_report_email.txt'
        self.data_source_content = None
        self.ignore_pattern = '^.*File\sReport$|^Generated|^$|^--|^Ready|^\s+Ready'
        self.ignore_rx = re.compile(self.ignore_pattern, re.IGNORECASE)
        self.last_transaction_date = None
        self.info_result_list = [
            'skipped',
            'expecting'
        ]
        self.success_result_list = [
            'found',
            'dq_success'
        ]
        self.warning_result_list = [
            'dq_not_run'
        ]
        self.danger_result_list = [
            'missing',
            'dq_error',
            'too_many_files',
            'too_many_manifests',
            'missing_manifest'
        ]
        self.ignore_result_types = [
            'info'
        ]
        self.last_file_type = None
        self.error_email_list = 'owen.hoyt@sas.com'  # ssowmtdev@wnt.sas.com
        self.environment = Environments()

    def set_body(self):
        self.log_it('In set_body for ' + str(self))
        self.build_summary()
        self.build_transaction_date_tables()

    def set_subject(self, data):
        self.subject = 'Walmart ' + data + ' AML HTML File Report | ' + datetime.today().strftime('%Y%m%d')
        return True

    def build_summary(self):
        summary_html_rows = ''
        for tran_dt in self.data:
            summary_row_vars = OrderedDict()
            summary_row_vars['status'] = self.data[tran_dt]['overall_status']
            summary_row_vars['tranDate'] = tran_dt
            summary_row_vars['textStatus'] = self.data[tran_dt]['text_status']
            summary_html_rows += self.get_view('summaryTranDateRow', summary_row_vars)

        self.body += self.get_view('summary', {'summaryHTMLRows': summary_html_rows})

    def post_email_send_handler(self):
        pass

    def build_transaction_date_tables(self):
        transaction_date_html_rows = ''
        for tran_dt in self.data:
            int_validator = IntValidator(True)
            first_row = True
            if not int_validator.validate(tran_dt):
                continue

            if self.data[tran_dt]['num_files'] < 1:
                continue

            transaction_date_html_rows += self.get_view('transactionDateHeaderRow')

            for file_type in self.data[tran_dt]:
                if not isinstance(self.data[tran_dt][file_type], dict) or self.data[tran_dt][file_type]['result'] in self.ignore_result_types:
                    continue
                tran_date_data_dict = {
                    'fileStatus': self.data[tran_dt][file_type]['result'],
                    'tranDate': tran_dt,
                    'fileType': file_type,
                    'fileName': self.build_filename_html(self.data[tran_dt][file_type]),
                    'fileStatusText': self.data[tran_dt][file_type]['normalized_status_text'],
                    'numFiles': str(self.data[tran_dt]['num_files']),
                    'batchStatus': str(self.data[tran_dt]['overall_status'])
                }

                if first_row:
                    transaction_date_html_rows += self.get_view('transactionDateRowFirst', tran_date_data_dict)
                    first_row = False
                else:
                    transaction_date_html_rows += self.get_view('transactionDateRow', tran_date_data_dict)

        self.body += self.get_view('transactionDateTable', {'transactionDateRows': transaction_date_html_rows})

    @staticmethod
    def build_filename_html(data):
        html = data['file_name_pattern']
        if len(data['multipleFiles']) > 0:
            html += '<ul>'
            for filename in data['multipleFiles']:
                html += '<li>' + filename + '</li>'
            html += '</ul>'

        return html

    def get_data(self):
        fev = FileExistsValidator(True)
        if not fev.validate(self.data_source):
            raise EmailException('Data source file does not exist: ' + fev.format_errors())
        self.log_it('In ' + str(self) + ' get_data()')
        with open(self.data_source) as f:
            self.data_source_content = f.readlines()

        self.data_source_content = [x.strip() for x in self.data_source_content]
        self.txt_only_version = self.data_source_content

        if len(self.data_source_content) < 1:
            raise EmailException('No data exists in ' + self.data_source)

        for line in self.data_source_content:
            if self.ignore_rx.match(line):
                self.log_it('Ignoring: ' + line)
                continue

            self.parse_data(line)

        self.log_it('===============================================================')
        self.log_it(json.dumps(self.data, indent=4))

    def parse_data(self, line):
        transaction_date_rx = re.compile('^Transaction\s+Date')
        if transaction_date_rx.match(line):
            transaction_date = re.sub("\D", "", line)
            self.last_transaction_date = transaction_date
            if transaction_date not in self.data:
                self.data[transaction_date] = {
                    'overall_status': 'success',
                    'text_status': 'Ready',
                    'num_files': 0
                }
                return True

        if not self.last_transaction_date:
            raise EmailException('Invalid transaction Date')

        status = None
        dq_status = None
        file_type = None
        file_name_pattern = None
        data_matched = False

        line_info_rx = re.compile('^([\w\s]+)\s+:\s+\[([\w\s]+)\]\s+(\w+)\s+\(([\w\d._/*]+)\)')
        line_info_rx2 = re.compile('^([\w\s]+):\s+\[([\w\s]+)\]\s+(\w+)\s+\(([\w\d._/*]+)\)')
        matches = line_info_rx.search(line)
        matches2 = line_info_rx2.search(line)
        if matches:
            status = matches.group(1).strip()
            dq_status = matches.group(2).strip()
            file_type = matches.group(3).strip()
            file_name_pattern = matches.group(4).strip()
            data_matched = True
            self.last_file_type = None
        elif matches2:
            status = matches2.group(1).strip()
            dq_status = matches2.group(2).strip()
            file_type = matches2.group(3).strip()
            file_name_pattern = matches2.group(4).strip()
            data_matched = True
            self.last_file_type = None
        else:
            line_info_rx = re.compile('^([\w\s]+)\s+:\s+(\w+)\s+\(([\w\d._/*]+)\)')
            line_info_rx2 = re.compile('^([\w\s]+):\s+(\w+)\s+\(([\w\d._/*]+)\)')
            matches = line_info_rx.search(line)
            matches2 = line_info_rx2.search(line)
            if matches:
                status = matches.group(1).strip()
                dq_status = 'N/A'
                file_type = matches.group(2).strip()
                file_name_pattern = matches.group(3).strip()
                data_matched = True
                self.last_file_type = None
            elif matches2:
                status = matches2.group(1).strip()
                dq_status = 'N/A'
                file_type = matches2.group(2).strip()
                file_name_pattern = matches2.group(3).strip()
                data_matched = True
                self.last_file_type = None
            elif self.last_file_type is not None:
                self.data[self.last_transaction_date][self.last_file_type]['multipleFiles'].append(line)

        if data_matched:
            if not file_type in self.data[self.last_transaction_date]:
                self.data[self.last_transaction_date][file_type] = {
                    'transaction_date': self.last_transaction_date,
                    'full_line': None,
                    'status': None,
                    'dq_status': None,
                    'file_type': None,
                    'file_name_pattern': None,
                    'normalized_status': None,
                    'normalized_status_text': None,
                    'result': None,
                    'multipleFiles': []
                }

            result_type = self.get_result(self.normalize_status(str(status), str(dq_status)))

            self.data[self.last_transaction_date][file_type]['full_line'] = str(line)
            self.data[self.last_transaction_date][file_type]['status'] = str(status)
            self.data[self.last_transaction_date][file_type]['dq_status'] = str(dq_status)
            self.data[self.last_transaction_date][file_type]['file_type'] = str(file_type)
            self.data[self.last_transaction_date][file_type]['file_name_pattern'] = str(file_name_pattern)
            self.data[self.last_transaction_date][file_type]['normalized_status'] = self.normalize_status(status, dq_status)
            self.data[self.last_transaction_date][file_type]['normalized_status_text'] = self.normalize_status_txt(status, dq_status)
            self.data[self.last_transaction_date][file_type]['result'] = str(result_type)
            self.data[self.last_transaction_date]['overall_status'] = self.set_overall_status_for_txn_dt(self.data[self.last_transaction_date][file_type]['result'])
            self.data[self.last_transaction_date]['text_status'] = self.normalize_text_status(self.data[self.last_transaction_date][file_type]['normalized_status'])
            if result_type not in self.ignore_result_types:
                self.data[self.last_transaction_date]['num_files'] = self.data[self.last_transaction_date]['num_files'] + 1

            if self.data[self.last_transaction_date][file_type]['normalized_status'] in ['too_many_files', 'too_many_manifests']:
                self.last_file_type = self.data[self.last_transaction_date][file_type]['file_type']

            self.update_batch_status(self.data[self.last_transaction_date][file_type]['normalized_status'], self.data[self.last_transaction_date][file_type]['full_line'])

        self.log_it('line: ' + str(line))
        self.log_it('transaction_dates: ' + self.last_transaction_date)
        self.log_it('status: ' + str(status))
        self.log_it('dq_status: ' + str(dq_status))
        self.log_it('file_type: ' + str(file_type))
        self.log_it('file_name_pattern: ' + str(file_name_pattern))

    @staticmethod
    def normalize_status(status, dq_status):
        if status == 'Missing File':
            return 'missing'
        elif status == 'Found':
            if dq_status == 'DQ SUCCESS':
                return 'dq_success'
            elif dq_status == 'DQ Error':
                return 'dq_error'
            elif dq_status == 'DQ Not Run':
                return 'dq_not_run'
            else:
                return 'found'
        elif status == 'Too Many Files':
            return 'too_many_files'
        elif status == 'Too Many Manifests':
            return 'too_many_manifests'
        elif status == 'Skipped':
            return 'skipped'
        elif status == 'Missing Manifest':
            return 'missing_manifest'
        elif status == 'Expecting File':
            return 'expecting'

    @staticmethod
    def normalize_status_txt(status, dq_status):
        if status == 'Found':
            if dq_status == 'DQ SUCCESS':
                return 'Found - DQ Success'
            elif dq_status == 'DQ Error':
                return 'Found - DQ Error'
            elif dq_status == 'DQ Not Run':
                return 'Found - DQ Not Run'
            else:
                return 'Found'
        else:
            return status

    def normalize_text_status(self, normalized_status):
        cur_status = str(self.data[self.last_transaction_date]['text_status']).split(',')
        if normalized_status == 'missing' and 'Missing File(s)' not in cur_status:
            cur_status.append('Missing File(s)')
        elif normalized_status == 'dq_error' and 'DQ Error(s)' not in cur_status:
            cur_status.append('DQ Errors(s)')
        elif normalized_status == 'dq_not_run' and 'DQ Not Run' not in cur_status:
            cur_status.append('DQ Not Run')
        elif normalized_status == 'too_many_files' and 'Too Many Files' not in cur_status:
            cur_status.append('Too Many Files')
        elif normalized_status == 'too_many_manifests' and 'Too Many Manifests' not in cur_status:
            cur_status.append('Too Many Manifests')
        elif normalized_status == 'missing_manifest' and 'Missing Manifest(s)' not in cur_status:
            cur_status.append('Missing Manifest(s)')

        if 'Ready' in cur_status and self.data[self.last_transaction_date]['overall_status'] != 'success':
            cur_status.remove('Ready')

        return ','.join(cur_status)

    def get_result(self, normalized_status):
        if normalized_status in self.info_result_list:
            return 'info'
        elif normalized_status in self.danger_result_list:
            return 'danger'
        elif normalized_status in self.success_result_list:
            return 'success'
        else:
            return 'warning'

    def set_overall_status_for_txn_dt(self, file_result):
        cur_overall_status = self.data[self.last_transaction_date]['overall_status']
        if cur_overall_status in ['danger']:
            return cur_overall_status
        elif cur_overall_status in ['warning']:
            if file_result in ['danger']:
                return file_result
            else:
                return cur_overall_status
        elif file_result == 'info':
            return 'success'
        else:
            return file_result

    def update_batch_status(self, normalized_status, file_report_line):
        try:
            send_status = False

            batch_status = None
            if normalized_status == 'missing':
                batch_status = 'MISSING_FILE'
                send_status = True
            elif normalized_status == 'dq_error':
                batch_status = 'DQ_ERROR'
                send_status = True
            elif normalized_status == 'too_many_files':
                batch_status = 'TOO_MANY_FILES'
                send_status = True
            elif normalized_status == 'too_many_manifests':
                batch_status = 'TOO_MANY_MANIFESTS'
                send_status = True
            elif normalized_status == 'missing_manifest':
                batch_status = 'MISSING_MANIFEST'
                send_status = True

            if send_status:
                if '_usd_' in file_report_line:
                    batch_cycle = 'USD_REPORT'
                else:
                    batch_cycle = 'DAILY_CYCLE'

                update_batch_status = UpdateBatchStatus()
                update_batch_status.update_batch_status(os.path.basename(__file__), batch_status, file_report_line, self.last_transaction_date, batch_cycle)

            return True
        except Exception as e:
            sas_email = SASEmail()
            sas_email.set_from('replies-disabled@sas.com')
            sas_email.set_to(self.error_email_list)
            sas_email.set_subject("[ERROR Updating Batch Status][" + self.environment.my_market + "][" + self.environment.my_hostname + "]")
            sas_email.set_text_message("Caught exception trying to update batch status: " + str(e) + "<br /><br />" + traceback.format_exc())
            sas_email.send()
