import os.path, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Exceptions import SsoZabbixWrapperException
from AbstractAMSZabbixWrapperHelper import AbstractAMSZabbixWrapperHelper

class CommTicketCommentOnlyHelper(AbstractAMSZabbixWrapperHelper):
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
        self.jibbix.project = self.project
        self.jibbix.link = 'comm'
        self.jibbix.comment_only = 'Yes'
        self.jibbix.security = 'sas'
        self.jibbix.description = dq_error_txt.strip()

    def __del__(self):
        """This is the destructor for DecryptPgP.  It will shred the file i.e. securely delete it."""
        pass