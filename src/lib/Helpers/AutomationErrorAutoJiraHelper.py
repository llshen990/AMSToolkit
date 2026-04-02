import os.path
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Exceptions import SsoZabbixWrapperException
from AbstractSsoZabbixWrapperHelper import AbstractSsoZabbixWrapperHelper

class AutomationErrorAutoJiraHelper(AbstractSsoZabbixWrapperHelper):
    def __init__(self):
        AbstractSsoZabbixWrapperHelper.__init__(self)
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
        """
        This method will get the watchers from the config file.
        :return: List of watchers.
        :rtype: str
        """
        if self.config.has_option('DEFAULT', 'dq_watchers'):
            return self.config.get('DEFAULT', 'dq_watchers')  # project is an optional flag used to add a project parameter onto the end of a zabbix key. So instead of batch.name, the zabbix key would be batch.name[tst]
        else:
            raise SsoZabbixWrapperException('Config does not contain dq_watchers variable')

    def _get_dq_master_ticket(self):
        """
        This will get the master ticket from the config file if any.
        :return: Jira Ticket Issue Key.
        :rtype: str
        """
        if self.config.has_option('DEFAULT', 'dq_master_ticket_link'):
            return self.config.get('DEFAULT', 'dq_master_ticket_link')  # project is an optional flag used to add a project parameter onto the end of a zabbix key. So instead of batch.name, the zabbix key would be batch.name[tst]
        else:
            raise SsoZabbixWrapperException('Config does not contain dq_master_ticket_link variable')

    def set_parameters(self, summary, description):
        """
        This method will set all necessary paramaters to properly trigger an AutomationErrorAutoJira ticket.
        :param summary: This is the summary as it would show up in Jira ticket.
        :type summary: str
        :param description: This is the description as it would show up in a Jira ticket.
        :type description: str
        :return: True upon success.
        :rtype: bool
        """

        # self.schedule_name = '[DQ ERROR] ' + os.path.basename(full_filename)
        assignee_str = '' if not self.assignee else "\nAssignee: " + self.assignee
        priority_str = 'Critical' if not self.priority else self.priority
        labels = self.project.strip() + '_Automation_Error'
        self.schedule_name = """Project: %s
Priority: %s
Link: comm
Component: Operations
Host: %s
Merge: yes
CommStatusPROD: |Not Normal%s
Watchers: %s
Summary: [AUTOMATION ERROR] %s
Labels: %s

%s
""" % (self.project, priority_str, self.hostname, assignee_str, self._get_watchers(), str(summary).strip(), labels, str(description).strip())
        self.batch_status = 'delay-message'

        return True

    def __del__(self):
        """This is the destructor for DecryptPgP.  It will shred the file i.e. securely delete it."""
        pass