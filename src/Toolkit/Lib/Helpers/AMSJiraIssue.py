import os
import sys

from jira import Issue

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)


class AMSJiraIssue(Issue):
    """ Jira Issue class preloaded with AMS defaults.
    This class extends the Issue class that is part of [this python Jira library](https://github.com/pycontribs/jira).
    This library is compliant with the official [Jira REST APIs](https://developer.atlassian.com/server/jira/platform/rest-apis/).
    Detailed documentation of the library can be found on [this page](https://jira.readthedocs.io/en/master/index.html).
    """

    def __init__(self, fields={}):
        self._fields = fields
        self._configure_default_fields()

    def fields(self):
        return self._fields

    def _configure_default_fields(self):
        """ Configure ETL OPS team specific JIRA fields """
        self.assign_project_key('SSO')
        self.assign_issue_type_by_name('ETL Ops SAS Service Request')
        self.assign_labels(['ams_toolkit'])
        self.add_priority_by_name()

        # custom fields
        AFFECTED_ENVIRONMENT = "customfield_16843"
        ETL_OPS_WORK_REQUEST = "customfield_16865"
        self._fields.update({
            AFFECTED_ENVIRONMENT: "SSO",
            ETL_OPS_WORK_REQUEST: {"value": "Consulting: Internal"}
        })

    def assign_project_key(self, key='SSO'):
        """ Assign a project key to an issue """
        self._fields.update({'project': {'key': key}})

    def assign_issue_type_by_name(self, issue_type_name='ETL Ops SAS Service Request'):
        """ Assign an issue type to an issue by name """
        self._fields.update({'issuetype': {'name': issue_type_name}})

    def add_summary(self, summary=''):
        self._fields.update({'summary': summary})

    def add_description(self, description=''):
        self._fields.update({'description': description})

    def add_assignee_by_name(self, assignee='etloperationssvcs'):
        self._fields.update({'assignee': {'name': assignee}})

    def add_due_date(self, due_date=''):
        self._fields.update({'duedate': due_date})

    def add_priority_by_name(self, priority='Minor'):
        self._fields.update({'priority': {'name': priority}})

    def assign_labels(self, labels=['ams_toolkit'], override=False):
        if self._fields.get('labels') and not override:
            labels.extend(self._fields.get('labels'))

        self._fields.update({'labels': labels})
