import os, sys, socket, collections

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSJibbixOptionsException
from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute
from lib.Helpers import OutputFormatHelper

ALLOWED_COMM_STATUS_VARS = [
    'prod',
    'test',
    'dev',
    'env_4',
    'env_5',
    'env_6',
]


class AMSJibbixOptions(AbstractAMSConfig):
    """
   This class defines the markets / environments
   """

    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.raw_config = collections.OrderedDict()
        self.project = None  # type: str
        self.priority = None  # type: str
        self.security = None  # type: str
        self.type = None  # type: str
        self.link = None  # type: str
        self.watchers = None  # type: str
        self.component = None  # type: str
        self.labels = None  # type: str
        self.merge = None  # type: str
        self.bundle = None  # type: str
        self.bundle_time = None  # type: int
        self.notify = None  # type: str
        self.comm_status_prod = None  # type: str
        self.comm_status_test = None  # type: str
        self.comm_status_dev = None  # type: str
        self.comm_status_env_4 = None  # type: str
        self.comm_status_env_5 = None  # type: str
        self.comm_status_env_6 = None  # type: str
        self.host = None  # type: str
        self.comment_only = None  # type: str
        self.summary = None  # type: str
        self.comment = None  # type: str
        self.schedule_name = None  # type: str
        self.assignee = None  # type: str
        self.description = None  # type: str

        self.allowed_comm_status_vars = ALLOWED_COMM_STATUS_VARS
        self.allowed_comment_only = [
            'yes'
        ]

    def get_config_dict_key(self):
        return ''

    def get_static_config_dict_key(self):
        return 'jibbix_options'

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """
        # to have description posted to Zabbix, which is not posted currently
        # My description
        description = AMSConfigModelAttribute()
        description.set_required(False)
        description.set_default(None)
        description.set_label('Description')
        description.set_type('str')
        description.set_allow_edit(False)
        description.set_mapped_class_variable('description')
        description.set_include_in_config_file(False)
        description.set_hide_from_user_display(True)
        self.config_model_attributes['description'] = description

        # My Hostname
        my_hostname_attrs = AMSConfigModelAttribute()
        my_hostname_attrs.set_required(True)
        my_hostname_attrs.set_default(self.my_hostname)
        my_hostname_attrs.set_label('My Hostname')
        my_hostname_attrs.set_type('str')
        my_hostname_attrs.set_allow_edit(False)
        my_hostname_attrs.set_mapped_class_variable('my_hostname')
        my_hostname_attrs.set_include_in_config_file(False)
        self.config_model_attributes['my_hostname'] = my_hostname_attrs

        # Project
        project_attrs = AMSConfigModelAttribute()
        project_attrs.set_required(True)
        project_attrs.set_default(None)
        project_attrs.set_label('JIRA Project (TLA)')
        project_attrs.set_type('str')
        project_attrs.set_mapped_class_variable('project')
        self.config_model_attributes['project'] = project_attrs

        # Assignee
        assignee_attrs = AMSConfigModelAttribute()
        assignee_attrs.set_required(True)
        assignee_attrs.set_default('ssoretailops')
        assignee_attrs.set_label('Assignee')
        assignee_attrs.set_type('str')
        assignee_attrs.set_mapped_class_variable('assignee')
        self.config_model_attributes['assignee'] = assignee_attrs

        # Priority
        priority_attrs = AMSConfigModelAttribute()
        priority_attrs.set_required(True)
        priority_attrs.set_default('critical')
        priority_attrs.set_label('Priority')
        priority_attrs.set_type('str')
        priority_attrs.set_options([
            'trivial',
            'minor',
            'major',
            'critical',
            'blocker'
        ])
        priority_attrs.set_mapped_class_variable('priority')
        self.config_model_attributes['priority'] = priority_attrs

        # Security
        security_attrs = AMSConfigModelAttribute()
        security_attrs.set_required(False)
        security_attrs.set_default('none')
        security_attrs.set_label('Security')
        security_attrs.set_type('str')
        security_attrs.set_options([
            'none',
            'sas',
            'sso'
        ])
        security_attrs.set_mapped_class_variable('security')
        self.config_model_attributes['security'] = security_attrs

        # Type
        type_attrs = AMSConfigModelAttribute()
        type_attrs.set_required(True)
        type_attrs.set_default('issue')
        type_attrs.set_label('Type')
        type_attrs.set_type('str')
        type_attrs.set_options([
            'issue',
            'task',
            'problem',
            'defect',
            'outage',
            'exception',
            'qaw'
        ])
        type_attrs.set_mapped_class_variable('type')
        self.config_model_attributes['type'] = type_attrs

        # Link
        link_attrs = AMSConfigModelAttribute()
        link_attrs.set_required(False)
        link_attrs.set_default(None)
        link_attrs.set_label('Link')
        link_attrs.set_type('str')
        link_attrs.set_mapped_class_variable('link')
        self.config_model_attributes['link'] = link_attrs

        # Watchers
        watchers_attrs = AMSConfigModelAttribute()
        watchers_attrs.set_required(False)
        watchers_attrs.set_default(None)
        watchers_attrs.set_label('Watchers (separated by commas)')
        watchers_attrs.set_type('str')
        watchers_attrs.set_mapped_class_variable('watchers')
        self.config_model_attributes['watchers'] = watchers_attrs

        # Component
        component_attrs = AMSConfigModelAttribute()
        component_attrs.set_required(False)
        component_attrs.set_default(None)
        component_attrs.set_label('Component (separated by commas)')
        component_attrs.set_type('str')
        component_attrs.set_mapped_class_variable('component')
        self.config_model_attributes['component'] = component_attrs

        # Labels
        labels_attrs = AMSConfigModelAttribute()
        labels_attrs.set_required(False)
        labels_attrs.set_default('ams_toolkit')
        labels_attrs.set_label('Labels (separated by commas)')
        labels_attrs.set_type('str')
        labels_attrs.set_mapped_class_variable('labels')
        self.config_model_attributes['labels'] = labels_attrs

        # Merge
        merge_attrs = AMSConfigModelAttribute()
        merge_attrs.set_required(False)
        merge_attrs.set_default('no')
        merge_attrs.set_label('Merge')
        merge_attrs.set_type('str')
        merge_attrs.set_options([
            'yes',
            'no',
            'simple',
            'skip'
        ])
        merge_attrs.set_mapped_class_variable('merge')
        self.config_model_attributes['merge'] = merge_attrs

        # Bundle
        bundle_attrs = AMSConfigModelAttribute()
        bundle_attrs.set_required(False)
        bundle_attrs.set_default(None)
        bundle_attrs.set_label('Bundle')
        bundle_attrs.set_type('str')
        bundle_attrs.set_mapped_class_variable('bundle')
        self.config_model_attributes['bundle'] = bundle_attrs

        # Bundle Time
        bundle_time_attrs = AMSConfigModelAttribute()
        bundle_time_attrs.set_required(False)
        bundle_time_attrs.set_default(None)
        bundle_time_attrs.set_label('Bundle Time')
        bundle_time_attrs.set_type('int')
        bundle_time_attrs.set_mapped_class_variable('bundle_time')
        self.config_model_attributes['bundle_time'] = bundle_time_attrs

        # Notify
        notify_attrs = AMSConfigModelAttribute()
        notify_attrs.set_required(False)
        notify_attrs.set_default('no')
        notify_attrs.set_label('Notify')
        notify_attrs.set_type('str')
        notify_attrs.set_options([
            'yes',
            'no'
        ])
        notify_attrs.set_mapped_class_variable('notify')
        self.config_model_attributes['notify'] = notify_attrs

        # Comm Statuses
        for comm_status in ALLOWED_COMM_STATUS_VARS:
            comm_status_attrs = AMSConfigModelAttribute()
            comm_status_attrs.set_required(False)
            comm_status_attrs.set_default(None)
            comm_status_attrs.set_label('Comm Status ' + comm_status.capitalize())
            comm_status_attrs.set_type('str')
            comm_status_attrs.set_options([
                'normal operations',
                'no activity',
                'not normal',
                'major issue',
                'maintenance'
            ])
            comm_status_attrs.set_mapped_class_variable('comm_status_' + comm_status)
            self.config_model_attributes['comm_status_' + comm_status] = comm_status_attrs

        # Summary
        summary_attrs = AMSConfigModelAttribute()
        summary_attrs.set_required(False)
        summary_attrs.set_default(None)
        summary_attrs.set_label('Summary')
        summary_attrs.set_type('str')
        summary_attrs.set_allow_edit(False)
        summary_attrs.set_mapped_class_variable('summary')
        self.config_model_attributes['summary'] = summary_attrs

        # Host
        host_attrs = AMSConfigModelAttribute()
        host_attrs.set_required(False)
        host_attrs.set_default(self.my_hostname)
        host_attrs.set_label('Host')
        host_attrs.set_type('str')
        host_attrs.set_allow_edit(False)
        host_attrs.set_mapped_class_variable('host')
        self.config_model_attributes['host'] = host_attrs

        # Comment Only
        comment_only_attrs = AMSConfigModelAttribute()
        comment_only_attrs.set_required(False)
        comment_only_attrs.set_default(None)
        comment_only_attrs.set_label('Comment Only')
        comment_only_attrs.set_type('str')
        comment_only_attrs.set_options([
            'yes'
        ])
        comment_only_attrs.set_mapped_class_variable('comment_only')
        self.config_model_attributes['comment_only'] = comment_only_attrs

    def load(self, schedule_name, config_dict):
        """
        :param schedule_name: schedule name from the config dict.
        :type schedule_name: str
        :param config_dict: AMS config dictionary (JSON)
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """
        try:
            self.raw_config = config_dict
            self.schedule_name = schedule_name.strip()
            self._read_project()
            self._read_priority()
            self._set_security()
            self._read_type()
            self._read_link()
            self._read_watchers()
            self._read_comment()
            self._read_merge()
            self._read_bundle()
            self._read_bundle_time()
            self._read_notify()
            for comm_status in self.allowed_comm_status_vars:
                self._read_comm_status(comm_status)
            self._read_comment_only()
            self._read_summary()
            self._read_assignee()
            self._read_component()
            self._read_labels()
            self._read_host()
            self._read_description()
        except AMSJibbixOptionsException:
            raise
        except Exception as e:
            raise AMSJibbixOptionsException(e)

    def _read_description(self):
        """
        This method will set description variable for the schedule. This is an optional override.
        :return: True upon success or False upon failure
        :rtype: bool
        """
        if 'description' in self.raw_config and self.raw_config['description']:
            self.description = str(self.raw_config['description']).strip()
        else:
            self.AMSLogger.debug('description is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_project(self):
        """
        This method will set the project variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'project' in self.raw_config and self.raw_config['project']:
            self.project = str(self.raw_config['project']).strip()
        else:
            self.AMSLogger.debug('project is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_priority(self):
        """
        This method will set the priority variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'priority' in self.raw_config and self.raw_config['priority']:
            priority_val = str(self.raw_config['priority']).strip().lower()
            if priority_val in self.get_config_attributes('priority').options:
                self.priority = priority_val
            else:
                self.AMSLogger.critical('Invalid priority given: ' + priority_val + '.  Valid options are: ' + OutputFormatHelper.join_output_from_list(self.get_config_attributes('priority').options))
                return False
        else:
            self.AMSLogger.debug('priority is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _set_security(self):
        """
        This method will set the security variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'security' in self.raw_config and self.raw_config['security']:
            security_val = str(self.raw_config['security']).strip().lower()
            if security_val in self.get_config_attributes('security').options:
                self.security = security_val
            else:
                self.AMSLogger.critical('Invalid security given: ' + security_val + '.  Valid options are: ' + OutputFormatHelper.join_output_from_list(self.get_config_attributes('security').options))
                return False
        else:
            self.AMSLogger.debug('security is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_type(self):
        """
        This method will set the type variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'type' in self.raw_config and self.raw_config['type']:
            type_val = str(self.raw_config['type']).strip().lower()
            if type_val in self.get_config_attributes('type').options:
                self.type = type_val
            else:
                self.AMSLogger.critical('Invalid type given: ' + type_val + '.  Valid options are: ' + OutputFormatHelper.join_output_from_list(self.get_config_attributes('type').options))
                return False
        else:
            self.AMSLogger.debug('type is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_link(self):
        """
        This method will set the link variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'link' in self.raw_config and self.raw_config['link']:
            self.link = str(self.raw_config['link']).strip()
        else:
            self.AMSLogger.debug('link is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_watchers(self):
        """
        This method will set the watchers variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'watchers' in self.raw_config and self.raw_config['watchers']:
            self.watchers = str(self.raw_config['watchers']).strip()
        else:
            self.AMSLogger.debug('watchers is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_component(self):
        """
        This method will set the component variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'component' in self.raw_config and self.raw_config['component']:
            self.component = str(self.raw_config['component']).strip()
        else:
            self.AMSLogger.debug('component is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_labels(self):
        """
        This method will set the labels variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'labels' in self.raw_config and self.raw_config['labels']:
            self.labels = str(self.raw_config['labels']).strip()
        else:
            self.AMSLogger.debug('labels is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_merge(self):
        """
        This method will set the component variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'merge' in self.raw_config and self.raw_config['merge']:
            merge_val = str(self.raw_config['merge']).strip().lower()
            if merge_val in self.get_config_attributes('merge').options:
                self.merge = merge_val
            else:
                self.AMSLogger.critical('Invalid merge given: ' + merge_val + '.  Valid options are: ' + OutputFormatHelper.join_output_from_list(self.get_config_attributes('merge').options))
                return False
        else:
            self.AMSLogger.debug('merge is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_bundle(self):
        """
        This method will set the bundle variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'bundle' in self.raw_config and self.raw_config['bundle']:
            self.bundle = str(self.raw_config['bundle']).strip()
        else:
            self.AMSLogger.debug('bundle is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_bundle_time(self):
        """
        This method will set the bundle_time variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'bundle_time' in self.raw_config and self.raw_config['bundle_time']:
            try:
                bundle_time_val = int(str(self.raw_config['bundle_time']).strip())
            except Exception as e:
                self.AMSLogger.critical('bundle_time requires any positive integer: ' + str(e))
                return False

            if bundle_time_val < 1:
                self.AMSLogger.critical('bundle_time requires any positive integer')
                return False

            self.bundle_time = bundle_time_val

        else:
            self.AMSLogger.debug('bundle_time is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_notify(self):
        """
        This method will set the notify variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'notify' in self.raw_config and self.raw_config['notify']:
            notify_val = str(self.raw_config['notify']).strip().lower()
            if notify_val in self.get_config_attributes('notify').options:
                self.notify = notify_val
            else:
                self.AMSLogger.critical('Invalid notify given: ' + notify_val + '.  Valid options are: ' + OutputFormatHelper.join_output_from_list(self.get_config_attributes('notify').options))
                return False
        else:
            self.AMSLogger.debug('notify is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_comm_status(self, comm_status_type):
        """
        This method will set the comm_status_<...> variable for the schedule.  This is an optional override.
        :param comm_status_type: This is the type of comm status variable to set.  i.e. prod, test, dev, env_4, env_5, env_6
        :type comm_status_type: str
        :return: True upon success or False upon failure.
        :rtype: bool
        """

        if comm_status_type not in self.allowed_comm_status_vars:
            self.AMSLogger.critical('Invalid comm_status variable given: ' + comm_status_type + '.  Valid options are: ' + OutputFormatHelper.join_output_from_list(self.allowed_comm_status_vars))
            return False

        comm_status_var = 'comm_status_' + comm_status_type

        if comm_status_var in self.raw_config and self.raw_config[comm_status_var]:
            comm_status_val = str(self.raw_config[comm_status_var]).strip().lower()
            if comm_status_val in self.get_config_attributes(comm_status_var).options:
                setattr(self, comm_status_var, comm_status_val)
            else:
                self.AMSLogger.info('Invalid ' + comm_status_var + ' given: ' + comm_status_val + '.  Valid options are: ' + OutputFormatHelper.join_output_from_list(self.get_config_attributes(comm_status_var).options))
                return False
        else:
            self.AMSLogger.debug('%s is not defined following schedule: %s.' % (comm_status_var, self.schedule_name))

        return True

    def _read_comment_only(self):
        """
        This method will set the comment_only variable for the schedule.  This is an optional override.
        :return: True upon success or exception upon failure.
        :rtype: bool
        """
        if 'comment_only' in self.raw_config and self.raw_config['comment_only']:
            comment_only_val = str(self.raw_config['comment_only']).strip().lower()
            if comment_only_val in self.get_config_attributes('comment_only').options:
                self.comment_only = comment_only_val
            else:
                self.AMSLogger.critical('Invalid comment_only given: ' + comment_only_val + '.  Valid options are: ' + OutputFormatHelper.join_output_from_list(self.get_config_attributes('comment_only').options))
                return False
        else:
            self.AMSLogger.debug('comment_only is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_summary(self):
        """
        This method will set the summary variable for the schedule.  This is an optional override.
        :return: True upon success or exception upon failure.
        :rtype: bool
        """
        if 'summary' in self.raw_config and self.raw_config['summary']:
            self.summary = str(self.raw_config['summary']).strip()
        else:
            self.AMSLogger.debug('summary is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_comment(self):
        """
        This method will set the comment variable for the schedule.  This is an optional override.
        :return: True upon success or exception upon failure.
        :rtype: bool
        """
        if 'comment' in self.raw_config and self.raw_config['comment']:
            self.comment = str(self.raw_config['comment']).strip()
        else:
            self.AMSLogger.debug('comment is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_assignee(self):
        """
        This method will set the assignee variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'assignee' in self.raw_config and self.raw_config['assignee']:
            self.assignee = str(self.raw_config['assignee']).strip()
        else:
            self.AMSLogger.debug('assignee is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def _read_host(self):
        """
        This method will set the link variable for the schedule.  This is an optional override.
        :return: True upon success or False upon failure.
        :rtype: bool
        """
        if 'host' in self.raw_config and self.raw_config['host']:
            self.host = str(self.raw_config['host']).strip()
        else:
            self.AMSLogger.debug('host is not defined for the following schedule: ' + self.schedule_name + '.')

        return True

    def should_be_sasserviceissue(self):
        if not self.type or self.type in ('issue', 'sasserviceissue'):
            return True
        else:
            return False

    def is_queue_assignee(self):
        if self.should_be_sasserviceissue():
            # Each of these queues are technically existing or operational queues for SAS Cloud
            if self.assignee in ('ssoretailops', 'etloperationsinciden', 'etloperationssvcs', 'sasadmins', 'amsteamjira'):
                return True
        return False

    def get_final_assignee(self):
        if self.is_queue_assignee():
            return "Operations Queue"
        elif self.assignee:
            return self.assignee
        else:
            return "Project Owner"

    def str_from_options(self):
        # See: https://www.ondemand.sas.com/confluencedoc/display/SSODCAM/CM+-+SSO+Performance+Team+Service+Catalog
        value = ""
        if self.project is not None:
            value += "Project: " + self.project + "\n"
        if self.priority is not None:
            value += "Priority: " + self.priority + "\n"
        if self.security is not None:
            value += "Security: " + self.security + "\n"

        # special handling if the type is issue or none (should default to issue)
        # in this case, we want to convert the ticket to a SAS Service Issue
        if self.should_be_sasserviceissue():
            # if we're trying to assign any of the legacy retail queues
            if self.is_queue_assignee():
                # in this case, we need to remove the 'ssoretailops' assignee and let the JIRA workflow assign it
                # this is because the queue will likely change in the future, so we'll manage that in JIRA instead
                self.assignee = None
            elif self.assignee:
                # here a specific assignee is being set with the "sascloud_use_direct_assignee" label so the JIRA
                # workflow for SAS Service Issue trusts to set the assignees
                # otherwise, the workflow will only set the assignee based off of the "Specific Issue"
                # See https://www.ondemand.sas.com/jira/browse/SSO-16722
                #
                # Please note, that we need to check for an assignee. If no assignee is provided, it will delegate to the workflow.
                # If you need to assign to the project owner, use ' ' or an empty space of a non-existent assignee like NEVERASSIGN
                if self.labels:
                    self.labels += ", sascloud_use_direct_assignee"
                else:
                    self.labels = "sascloud_use_direct_assignee"

            value += "Type: sasserviceissue\n"
            value += 'customfield_17185: Batch Issues / Bad Data\n'
            value += 'customfield_16863: Not provided\n'
            value += 'customfield_16843: {}\n'.format(self.my_hostname)
        else:
            value += "Type: " + self.type + "\n"
        if self.link is not None:
            value += "Link: " + self.link + "\n"
        if self.component is not None:
            value += "Component: " + self.component + "\n"
        if self.labels is not None:
            value += "Labels: " + self.labels + "\n"
        if self.assignee is not None:
            value += "Assignee: " + self.assignee + "\n"
        if self.watchers is not None:
            value += "Watchers: " + self.watchers + "\n"
        if self.merge is not None:
            value += "Merge: " + self.merge + "\n"
        if self.notify is not None:
            value += "Notify: " + self.notify + "\n"
        if self.bundle is not None:
            value += "Bundle: " + self.bundle + "\n"
        if self.bundle_time is not None:
            value += "Bundle_Time: " + str(self.bundle_time) + "\n"
        # We've seen problems with the Communications ticket being closed
        # To help diagnose adding a Summary that will only appear when that situation occurs
        if self.comment_only is not None:
            value += "CommentOnly: " + self.comment_only + "\n"
            value += "Summary: Link to {} ticket in project {}".format(self.link, self.project) + "\n"
        elif self.summary is not None:
            value += "Summary: " + self.summary + "\n"
        if self.comment is not None:
            value += "Comment: " + self.comment + "\n"
        if self.host is not None:
            value += "Host: " + self.host + "\n"
        if self.comm_status_dev is not None:
            # value += "CommStatusDev: " + self.comm_status_dev + "\n"
            value += "CommStatusDev: " + str(self.host) + ' | '+str(self.comm_status_dev).title() + "\n"
        if self.comm_status_test is not None:
            # value += "CommStatusTest: " + self.comm_status_test + "\n"
            value += "CommStatusTest: " + str(self.host) + ' | '+str(self.comm_status_test).title() + "\n"
        if self.comm_status_prod is not None:
            # value += "CommStatusProd: " + self.comm_status_prod + "\n"
            value += "CommStatusProd: " + str(self.host) + ' | '+str(self.comm_status_prod).title() + "\n"
        if self.comm_status_env_4 is not None:
            # value += "CommStatusEnv_4: " + self.comm_status_env_4 + "\n"
            value += "CommStatusEnv_4: " + str(self.host) + ' | '+str(self.comm_status_env_4).title() + "\n"
        if self.comm_status_env_5 is not None:
            # value += "CommStatusEnv_5: " + self.comm_status_env_5 + "\n"
            value += "CommStatusEnv_5: " + str(self.host) + ' | '+str(self.comm_status_env_5).title() + "\n"
        if self.comm_status_env_6 is not None:
            # value += "CommStatusEnv_6: " + self.comm_status_env_6 + "\n"
            value += "CommStatusEnv_6: " + str(self.host) + ' | '+str(self.comm_status_env_6).title() + "\n"
        if self.description is not None:
            value += 'Description: ' + self.description + '\n'
        return value

    def __str__(self):
        """
        magic method when to return the class name when calling this object as a string
        :return: Returns the class name
        :rtype: str
        """
        return self.__class__.__name__

    def __del__(self):
        pass

    # def _validate_link(self,raw_input):
    #     if len(raw_input)==0:
    #         return True
    #     return self.uv.validate(raw_input)
