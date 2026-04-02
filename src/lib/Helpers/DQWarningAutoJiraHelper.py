import os.path, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from lib.Exceptions import SsoZabbixWrapperException
from AbstractAMSZabbixWrapperHelper import AbstractAMSZabbixWrapperHelper
from lib.Helpers import FileGetFileType

class DQWarningAutoJiraHelper(AbstractAMSZabbixWrapperHelper):
    def __init__(self):
        AbstractAMSZabbixWrapperHelper.__init__(self)
        pass

    def _add_project_arg(self):
        """
        Want to override adding the project so that it's never set for WMT in DQ.
        """
        return self

    def _add_priority_arg(self):
        """
        Want to override adding the priority so that it's never set for WMT in DQ.
        """
        return self

    def _get_watchers(self):
        if self.config.has_option('DEFAULT', 'dq_watchers'):
            return self.config.get('DEFAULT', 'dq_watchers')  # project is an optional flag used to add a project parameter onto the end of a zabbix key. So instead of batch.name, the zabbix key would be batch.name[tst]
        else:
            raise SsoZabbixWrapperException('Config does not contain dq_watchers variable')

    def _get_dq_master_ticket(self):
        if self.config.has_option('DEFAULT', 'dq_master_ticket_link'):
            return self.config.get('DEFAULT', 'dq_master_ticket_link')  # project is an optional flag used to add a project parameter onto the end of a zabbix key. So instead of batch.name, the zabbix key would be batch.name[tst]
        else:
            raise SsoZabbixWrapperException('Config does not contain dq_master_ticket_link variable')

    def set_parameters(self, full_filename, dq_error_txt):
        fev = FileExistsValidator(True)
        if not (fev.validate(full_filename)):
            raise SsoZabbixWrapperException('ETL file does not exist: ' + full_filename)

        file_type_obj = FileGetFileType()
        try:
            file_type_str = file_type_obj.get_file_type_from_filename(full_filename)
        except Exception as e:
            file_type_str = 'Unknown'
        priority_str = 'Minor' if not self.priority else self.priority
        labels = 'Data_Quality,' + self.project.strip() + '_' + file_type_str + ',DQ_Warning'
        extra_link = '' if not self._get_dq_master_ticket() else "," + self._get_dq_master_ticket()
        self.jibbix.project = self.project
        self.jibbix.priority = priority_str
        self.jibbix.link = 'comm{}'.format(extra_link)
        self.jibbix.component = 'Operations'
        self.jibbix.comm_status_prod = '{}|Major Issue'.format(self.hostname)
        self.jibbix.assignee = self.assignee
        self.jibbix.watchers = self._get_watchers()
        self.jibbix.summary = '[DQ WARNING: {}] {} | {}'.format(self.hostname, os.path.basename(full_filename), file_type_str)
        self.jibbix.labels = labels
        self.jibbix.description = dq_error_txt.strip()

    def __del__(self):
        """This is the destructor for DecryptPgP.  It will shred the file i.e. securely delete it."""
        pass