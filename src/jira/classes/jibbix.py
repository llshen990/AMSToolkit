#!/usr/bin/env python

# Purpose: Used by Zabbix to create JIRA ticket from action
# Author: Ryan Younce
# Rewrite: Jerry Chen  02/03/2016
# Updated: Owen Hoyt 01/30/2017

# Usage: jibbix.py 'userid' 'title' 'body'
#
# Body contains JIRA option section and JIRA description section, separated by a blank line.
# Lines starting with # in option section are ignored.
#
# Supported JIRA options:
#
# Project: <TLA> (required)
# Priority: blocker, critical (default), major, minor, trivial
# Security: none (default), sas (SAS only), sso (SSO only)
# Type: issue (default), task, problem, outage, defect, exception, qaw
# Link: none (default), comm (Communications Ticket), <ticket> | Specify multiple links separated by commas
# Watchers: list of users in format of user1, user2, ...
# Labels: list of labels in format of label1, label2, ...
# Component: Operations or Implementation, or other defined component | Specify multiple links separated by commas
# Merge: no (default, not checking duplicate), yes (merge into previous ticket), skip (do nothing if duplicate is found)
# Notify: yes (default, if failed try again in ZABIX project), no
# CommStatusPROD: <hostname1,hostname2>|<status> | Defaults: All hosts and status of 'Normal Operations'.
# CommStatusTEST: <hostname1,hostname2>|<status> | Defaults: All hosts and status of 'Normal Operations'.
# CommStatusDEV: <hostname1,hostname2>|<status> | Defaults: All hosts and status of 'Normal Operations'.
# CommStatusENV_4: <hostname1,hostname2>|<status> | Defaults: All hosts and status of 'Normal Operations'.
# CommStatusENV_5: <hostname1,hostname2>|<status> | Defaults: All hosts and status of 'Normal Operations'.
# CommStatusENV_6: <hostname1,hostname2>|<status> | Defaults: All hosts and status of 'Normal Operations'.
# Host: {HOST.HOST} | This is required to use CommStatus<n> variables above.  This is the FQDN.
# CommentOnly: True | Must have a value of True (any case) in order for this option to be used.
#              Will only comment on linked ticket(s). | Used with Project and Security (optional).
#              Body will be the 'comment' to add.

# Zabbix action message example:
#
# Project: TST
# Priority: minor
# Type: task
# Link: comm
#
# JIRA ticket description starts from here
# ...

import traceback
import StringIO
import base64
import json
import logging
import os
import re
import sys
import urllib2
import collections

import argparse

import jira_secret

# Default log location
if os.path.basename(__file__) == 'jibbix.py':
    LOG = '/sso/sfw/zabbix/var/log/jibbix.log'
else:
    LOG = '/sso/sfw/zabbix/var/log/jibbix-beta.log'

# REST API end point for JIRA
URL = 'https://www.ondemand.sas.com/jira/rest/api/2'

# Logging handler
logger = logging.getLogger()

# JIRA Priority
class Priority(object):
    blocker = '1'
    critical = '2'
    major = '3'
    minor = '4'
    trival = '5'

    @staticmethod
    def get_id(val):
        return getattr(Priority, val, Priority.critical)

# JIRA Security
class Security(object):
    none = '-1'
    sas = '10010'
    internal = sas
    isd = '10071'
    sso = '10020'

    @staticmethod
    def get_id(val):
        return getattr(Security, val, Security.none)

# JIRA Issue Type
class Type(object):
    issue = '1'
    task = '3'
    subtask = '10'
    outage = '17'
    exception = '101'
    problem = '81'
    defect = '8'
    qaw = '13'

    @staticmethod
    def get_id(val):
        return getattr(Type, val, Type.issue)

# Direct logging to specified log file. If not provided, direct to standard output
def set_logging(log_file=''):
    global logger

    if log_file in ('', 'stdout', 'sys.stdout'):
        # sys.stdout
        ch = logging.StreamHandler(sys.stdout)
    else:
        ch = logging.FileHandler(log_file)

        # formatter = logging.Formatter("%(asctime)s [%(process)-5d] %(name)-6s %(levelname)-7s %(message)s")
    formatter = logging.Formatter("%(asctime)s [%(process)-5d] %(levelname)-7s %(message)s")
    ch.setFormatter(formatter)

    logger = logging.getLogger('jibbix')
    logger.setLevel(logging.INFO)
    logger.addHandler(ch)

set_logging('stdout')

# Info on Zabbix action
class Info(object):
    # noinspection PyShadowingNames
    def __init__(self, config=None):

        # Project is required
        self.project = '_NONE_'

        # If provided (not auto), overwrites recipient
        self.assignee = 'auto'

        # Summary or title of ticket
        self.summary = 'Opened by Zabbix'

        # Default Priority is Critical
        self.priority = 'critical'

        # Default Security is open to all
        self.security = 'none'

        # Default Type is Issue
        self.type = 'issue'

        # Default link is none
        self.link = 'none'

        # If provided, the value has to be case-sensitive (except Implementation, Operations)
        self.component = None

        # labels can be separated by either blank or comma. case-sensitive.
        self.labels = None

        # If provided, each watcher is added to the ticket
        self.watchers = ''

        # By default, do not merge this into existing ticket
        self.merge = 'no'

        # By default, if new ticket fails to open, try open it under ZABIX
        self.notify = 'yes'

        # Default Description
        self.description = 'This is default description.'

        # If provided, add a comment to new ticket or use it to replace description for existing ticket.
        self.comment = None

        # host
        self.host = None

        # Comment Only
        self.commentOnly = False

        # Parent Issue (subtasks)
        self.parent = None

        # Start Comm ticket only options below
        self.commStatus = {
            'CommStatusPROD': {
                'line': None,
                'parsedLine': None,
                'customField': 'customfield_14882',
                'status': None
            },
            'CommStatusTEST': {
                'line': None,
                'parsedLine': None,
                'customField': 'customfield_14883',
                'status': None
            },
            'CommStatusDEV': {
                'line': None,
                'parsedLine': None,
                'customField': 'customfield_14885',
                'status': None
            },
            'CommStatusENV_4': {
                'line': None,
                'parsedLine': None,
                'customField': 'customfield_14884',
                'status': None
            },
            'CommStatusENV_5': {
                'line': None,
                'parsedLine': None,
                'customField': 'customfield_14886',
                'status': None
            },
            'CommStatusENV_6': {
                'line': None,
                'parsedLine': None,
                'customField': 'customfield_14985',
                'status': None
            },
        }

        self.allowedCommStatus = {
            'normal operations': 'Normal Operations',
            'no activity': 'No Activity',
            'not normal': 'Not Normal',
            'major issue': 'Major Issue',
            'maintenance': 'Maintenance'
        }

        self.updateCommStatus = False
        self.invalidCommStatusFields = None
        # End Comm ticket only options

        if config:
            self.assignee = config.recipient
            self.summary = config.subject
            self.body = config.body
            logger.info('Extracted recipient=[%s]' % config.recipient)
            logger.info('Extracted subject=[%s]' % config.subject)

    # Parse the body argument (from Zabbix action's Default Message)
    def parse_body(self):
        regex = re.compile(r"(?P<name>[a-zA-Z_456]+[^:]):\s*(?P<value>.*?)\s*$")
        comm_status_regex = re.compile("CommStatus[PRODTESVN_456]+:(.*)")
        message = None

        body_io = StringIO.StringIO(self.body)

        for line in body_io:
            if line.find('#') == 0:
                continue

            match = regex.match(line)

            if match:
                name = match.group('name').lower()
                val = match.group('value')
                comm_status_regex_match = comm_status_regex.match(line)

                if name == 'project':
                    val = val.upper()
                elif name in ['component', 'labels']:
                    # Not changing to lower cases for these fields
                    pass
                elif comm_status_regex_match:
                    # Since we need the host variable, we'll parse the whole message and at the end
                    # go back and set the commStatus to make sure
                    self.commStatus[str(match.group('name')).strip()]['line'] = line.strip()
                elif name == 'commentonly':
                    val = str(val).strip().lower()
                    if val == 'true':
                        self.commentOnly = True
                else:
                    val = val.lower()
                if not comm_status_regex_match:
                    setattr(self, name, val)
                    logger.info('Extracted %s=[%s]' % (name, val))

            else:
                if line.strip():
                    message = line
                break

        for line in body_io:
            if message:
                message += line
            elif line.strip():
                message = line

        self.description = message

        # now we loop through self.commStatus to properly parse out the comm status fields
        # as we should have the host field set if one was provided.
        if self.link.find('comm') == 0:
            for statusField in self.commStatus:
                if self.commStatus[statusField]['line']:
                    self.parse_comm_status(statusField)

    def parse_comm_status(self, comm_status_level):
        """
        This method parses a CommStatus line in the zabbix message.
        :param comm_status_level: This is the exact comm status field
        :return: bool
        """

        if not self.host:
            return True

        host_included = False
        line_stripped = re.sub('^' + comm_status_level + ':', '', str(self.commStatus[comm_status_level]['line']))
        line_parts = line_stripped.split('|')
        if len(line_parts) < 2:
            line_parts.append('')
        comm_status = self.allowedCommStatus[self.check_comm_status(line_parts[1], comm_status_level)]

        line_parts[0] = line_parts[0].strip()
        line_parts[1] = line_parts[1].strip()

        if not line_parts[0] or line_parts[0] == '':
            # if no host names specified, default to all hosts to PROD
            host_included = True
        else:
            hosts = line_parts[0].split(',')
            for host in hosts:
                if str(host).strip().lower() == self.host.lower():
                    host_included = True
                    break

        if host_included:
            if not comm_status:
                self.commStatus[comm_status_level]['status'] = comm_status
            else:
                self.commStatus[comm_status_level]['status'] = {
                    "value": comm_status
                }
            self.commStatus[comm_status_level]['parsedLine'] = True
            self.updateCommStatus = True

        return True

    def check_comm_status(self, status, comm_status_level):
        status = str(status).strip().lower()
        if status not in self.allowedCommStatus:
            if not self.invalidCommStatusFields:
                self.invalidCommStatusFields = "Invalid status specified for the following comm status fields:\n"
                self.invalidCommStatusFields += comm_status_level + ': ' + status
            else:
                self.invalidCommStatusFields += "\n" + comm_status_level + ': ' + status
            return 'normal operations'
        return status

# JIRA ticket class
# noinspection PyShadowingBuiltins
class Jira(object):
    def __init__(self, key=None):
        self.key = key
        self.result = ''
        self.error = None
        self.rest_method = 'POST'
        self.data = {}
        self.info = None
        self.response = None
        self.resp_json = {}
        self.action = ''
        self.fields = collections.OrderedDict()
        self.update_fields = {}

    def get_comm_ticket_jql(self, info_obj, tmp_link):
        """
        :param info_obj: Info object passed in coming from parsed zabbix input.
        :type info_obj: Info
        :param tmp_link: Link string passed in the Link: field.
        :type tmp_link: str
        :return: Comm ticket JQL string.
        :rtype: str
        """

        p_key = self.get_p_key_from_info(info_obj, tmp_link)

        jql = "Project=%s and Status in ('reopened', 'open') and Type=Communications" % p_key
        return jql

    @staticmethod
    def get_p_key_from_info(info_obj, tmp_link):
        """
        :param info_obj: Info object passed in coming from parsed zabbix input.
        :type info_obj: Info
        :param tmp_link: Link string passed in the Link: field.
        :type tmp_link: str
        :return: Comm ticket JQL string.
        :rtype: str
        """
        if tmp_link == 'comm':
            p_key = info_obj.project
        else:
            # Example: comm.SBY
            p_key = tmp_link[5:].upper()

        return p_key

    # Map extracted Zabbix data to JIRA data
    # noinspection PyShadowingNames
    def map_data(self, info):
        """
        :type info: Info
        """
        self.info = info

        p_key = info.project
        self.fields['project'] = {
            'key': p_key
        }

        if info.parent is not None:
            self.fields['parent'] = {
                'key': info.parent
            }

        id = Type.get_id(info.type)
        self.fields['issuetype'] = {
            'id': id
        }

        id = Priority.get_id(info.priority)
        self.fields['priority'] = {
            'id': id
        }

        # Some projects (like TST) do not have security enabled, so ommit the field if none.
        # For SOK issue, see ZABIX-1832.
        id = Security.get_id(info.security)
        if id != Security.none:
            if p_key in ('TST', 'ITM', 'INTSA', 'MISTK', 'SOK'):
                logger.info('Security level is not supported for %s. Ignored.' % p_key)
            else:
                self.fields['security'] = {
                    'id': id
                }

        a_name = info.assignee or 'auto'
        if a_name not in ('<default>', 'auto', ''):
            self.fields['assignee'] = {
                'name': a_name
            }

        if info.labels:
            self.fields['labels'] = info.labels.replace(',', ' ').split()

        self.fields['summary'] = info.summary
        self.fields['description'] = info.description

        self.data = {
            "fields": self.fields
        }

    # Submit request through JIRA REST API
    def submit(self):
        self.result = ''

        logger.info("REST Action: %s/%s %s" % (URL, self.action, self.rest_method))

        request = urllib2.Request(URL + "/" + self.action)
        request.add_header('Content-Type', 'application/json')
        request.add_header('Accept', 'application/json')
        auth = base64.b64encode(jira_secret.user + ":" + jira_secret.password)
        request.add_header('Authorization', 'Basic %s' % auth)

        if self.rest_method == 'PUT':
            request.get_method = lambda: 'PUT'

        if self.data:
            json_str = json.dumps(self.data)
            print json.dumps(self.data, indent=4)
            request.add_data(json_str)
            logger.info("REST Data: " + json_str)

        try:
            self.response = urllib2.urlopen(request).read()
            print self.response
        except Exception as e:
            print 'Exception: ' + str(e)
            print traceback.print_exc()
            error_message = e.read()
            print error_message
            logger.info(e)
            self.result = 'Failed'
            self.error = str(e)
            logger.info(self.error[:256])
            return

            # print self.response

        if self.response:
            self.resp_json = json.loads(self.response)
        else:
            self.resp_json = {}

        print json.dumps(self.resp_json, indent=4)

    # Create a new ticket
    # noinspection PyShadowingNames
    def create(self, info):
        """
        :type info: Info
        """
        # set_logging('stdout')

        if info.project == '_NONE_':
            self.result = 'Failed'
            self.error = '{"project":"Project is missing"}'
            logger.info(self.error)
            return

        # Search for the duplicated issue that is still open
        # This cuts down the number of tickets that look the same
        # Sample JQL: Project=BLS and Status!=Closed and Summary~"pattern" and Created>="2016-07-01"
        if info.merge in ('yes', 'skip'):
            logger.info('Checking duplicate ticket...')

            # dash interferes with title matching
            summary = info.summary.lower()
            summary = summary.replace('-', ' ')

            # Remove key word RECOVERD or OK: from summary to accommodate typical recovery message
            summary = summary.replace('recovered', '').replace('ok:', '')

            # Search duplicate ticket in same project and not closed/resolved yet
            jql = "Project=%s and Status not in (closed, resolved) and Reporter=sso_zabbix and Summary~\"%s\" order by created desc" % (info.project, summary)
            self.search(jql)

            # Case for error
            if self.result == 'Failed': return

            # Case for duplicate found
            if self.result == 'Found' and self.key:
                # Do nothing if skip is specified
                if info.merge == 'skip':
                    logger.info('Skip duplicated ticket.')
                    self.result = 'Skipped'
                    return
                # Add description as new comment, but use comment data instead if specified
                comment = info.comment or info.description
                self.add_comment(comment)
                self.result = 'Merged'
                return

        # Create new ticket

        self.rest_method = 'POST'
        self.action = 'issue'
        self.map_data(info)
        self.submit()

        if self.result == 'Failed': return

        self.key = self.resp_json.get('key')
        self.result = 'Created'

        logger.info('Success: Created ticket %s', self.key)

        if info.comment:
            self.add_comment(info.comment)

    # Add a comment to ticket
    def add_comment(self, comment, sec=Security.sas, key_for_comment=None):
        if not key_for_comment:
            key_for_comment = self.key
        self.rest_method = 'POST'
        self.action = 'issue/%s/comment' % key_for_comment
        vis = {}
        if sec == Security.sso:
            vis = {
                'type': 'group',
                'value': 'SAS Internal - ASP'
            }
        if sec in (Security.sas, Security.internal):
            vis = {
                'type': 'group',
                'value': 'SAS Internal - All'
            }
        self.data = {
            'body': comment,
            'visibility': vis
        }
        self.submit()
        if self.result == 'Failed':
            logger.error("[COMMENT_FAILED] Failed to add comment to key: %s.%sError: %s" % (key_for_comment, os.linesep, self.error))
            return
        self.result = 'Appended'
        logger.info("Success: Added comment to %s" % key_for_comment)

    # Get ticket summary
    def get_summary(self):
        self.rest_method = 'GET'
        self.action = 'issue/%s?fields=key,summary' % self.key
        self.data = None
        self.submit()
        if self.result == 'Failed': return
        return self.resp_json.get('summary')

    # Add a watcher
    def add_watcher(self, name):
        self.rest_method = 'POST'
        self.action = 'issue/%s/watchers' % self.key
        self.data = name
        self.submit()
        if self.result == 'Failed': return
        self.result = 'Added'
        logger.info("Success: Added watcher %s to %s" % (name, self.key))

    # Add a component
    def add_component(self, name):
        self.rest_method = 'PUT'
        self.action = 'issue/%s' % self.key
        self.data = {
            'update': {
                'components': [{
                    'add': {
                        'name': name
                    }
                }]
            }
        }
        self.submit()
        if self.result == 'Failed': return
        self.result = 'Added'
        logger.info("Success: Added component %s to %s" % (name, self.key))

    # Search a ticket with JQL
    # noinspection PyShadowingBuiltins
    def search(self, jql, max=1):
        self.rest_method = 'GET'
        self.action = 'search'
        self.data = {
            'fields': ['key'],
            'maxResults': max,
            'jql': jql
        }
        self.key = None
        self.submit()

        if self.result == 'Failed': return None

        issues = self.resp_json.get('issues')
        if issues:
            self.result = 'Found'
            self.key = issues[0].get('key')
            logger.info('Success: Found ticket %s', self.key)
            return self.key
        else:
            self.result = 'Not Found'
            logger.info('Success: No ticket is found.')
            return None

    # Link two tickets
    def link_to(self, key):
        self.rest_method = 'POST'
        self.action = 'issueLink'
        self.data = {
            'type': {
                'name': 'Relates to'
            },
            'inwardIssue': {
                'key': key
            },
            'outwardIssue': {
                'key': self.key
            },
        }
        self.submit()
        if self.result == 'Failed': return
        self.result = 'Linked'
        logger.info("Success: Linked %s to %s" % (self.key, key))

    def update_issue(self):
        self.rest_method = 'PUT'
        self.action = self.action = 'issue/%s' % self.key
        self.data = {
            'fields': self.update_fields
        }
        self.submit()
        if self.result == 'Failed': return
        self.result = 'Updated'
        logger.info("Success: updated issue key: %s with: %s" % (self.key, str(self.update_fields)))
        # print "Success: updated issue key: %s with: %s" % (self.key, str(self.update_fields))

    def add_field_to_update(self, key, value):
        try:
            self.update_fields[key] = value
            logger.info("[add_field_to_update] %s => %s" % (key, str(value)))
            return True
        except Exception as e:
            logger.error("Exception in add_field_to_update: %s" % str(e))
            return False

# create ZABIX ticket for error handling
def create_error_ticket(info_obj, error_comment):
    """
    :param info_obj: Info object passed in coming from parsed zabbix input.
    :type info_obj: Info
    :param error_comment: Comment to add for error ticket.
    :type error_comment: str
    :return: True upon success, False on failure
    :rtype: bool
    """
    if not error_comment or error_comment.strip() == '':
        error_comment = 'Jibbix is in error state and no error condition comment specified.'
    info_obj.project = 'ZABIX'
    info_obj.comment = error_comment
    zab = Jira()
    zab.create(info_obj)
    return zab

# Search existing JIRA ticket
def search_ticket(jql):
    jira_obj = Jira()
    jira_obj.search(jql)
    return jira_obj

def comment_only(info_obj):
    """
    :param info_obj: Info object passed in coming from parsed zabbix input.
    :type info_obj: Info
    :return: True upon success, False on failure
    :rtype: bool
    """

    if info_obj.link != 'none':
        tmp_link_ary = info_obj.link.split(',')
        if tmp_link_ary and len(tmp_link_ary) > 0:
            one_success = False
            for tmp_link in tmp_link_ary:
                tmp_link = str(tmp_link).strip()
                # Link to the open communication ticket of same project
                if tmp_link.find('comm') == 0:
                    jira_obj = Jira()
                    jira_obj.search(jira_obj.get_comm_ticket_jql(info_obj, tmp_link))

                    if jira_obj.result == 'Found' and jira_obj.key:
                        jira_obj.add_comment(info_obj.description, Security.get_id(info_obj.security))
                        one_success = True
                    else:
                        create_error_ticket(info_obj, "Unable to link to %s Communications ticket" % jira_obj.get_p_key_from_info(info_obj, tmp_link))
                        logger.error("[COMMENT_ONLY] Unable to link to %s Communications ticket" % jira_obj.get_p_key_from_info(info_obj, tmp_link))
                else:
                    # Link to a specific ticket, if provided
                    jira_obj = Jira(key=tmp_link)
                    jira_obj.add_comment(info_obj.description, Security.get_id(info_obj.security))
                    one_success = True

            return one_success
        else:
            create_error_ticket(info_obj, "Unable to add comment as no 'link:' was specified - list is empty.")
            logger.error("[COMMENT_ONLY] Unable to add comment as no 'link:' list is empty.")
            return False
    else:
        create_error_ticket(info_obj, "Unable to add comment as no 'link:' info was specified.")
        logger.error("[COMMENT_ONLY] Unable to add comment as no 'link:' info was specified.")
        return False

# Open a JIRA ticket and if needed perform additional actions specified in info object
# noinspection PyShadowingNames
def open_ticket(info):
    """
    :param info: Info object passed in coming from parsed zabbix input.
    :type info: Info
    :return: Jira Class
    :rtype: Jira
    """
    jira = Jira()
    jira.create(info)

    # If there is error in creating the ticket, open a ZABIX ticket for attention
    if jira.result == 'Failed':

        # Not if setting is NO
        if info.notify != 'yes': return None

        # if it is user assignment error, assign to project owner
        if jira.error.find('"assignee":') > 0:
            info.comment = 'Unable to assign to %s. Assigned to project owner.' % info.assignee
            info.assignee = 'auto'
            jira.create(info)

        # if it is project value error, create it under ZABIX
        elif jira.error.find('"project":') >= 0:

            # target_project = info.project
            info.project = 'ZABIX'
            info.comment = 'Project is missing or incorrect.'
            zab = Jira()
            zab.create(info)
            return zab

        else:
            return None

    if jira.result != 'Created': return None

    if info.link != 'none':
        tmp_link_ary = info.link.split(',')
        if tmp_link_ary and len(tmp_link_ary) > 0:
            for tmp_link in tmp_link_ary:
                tmp_link = str(tmp_link).strip()
                # Link to the open communication ticket of same project
                if tmp_link.find('comm') == 0:
                    c = Jira()
                    c.search(c.get_comm_ticket_jql(info, tmp_link))

                    if c.result == 'Found' and c.key:
                        jira.link_to(c.key)
                        # since we just opened a new ticket and linked it to the Comm ticket,
                        # we're going to update the comm ticket with a comment to update the
                        # VA report.
                        c.add_comment('Report: ' + jira.key + ' - ' + jira.fields['summary'], Security.none)

                        # let's now check if we need to update any of the status fields for the COMM ticket
                        if info.updateCommStatus:
                            for statusField in info.commStatus:
                                if info.commStatus[statusField]['parsedLine']:
                                    c.add_field_to_update(info.commStatus[statusField]['customField'], info.commStatus[statusField]['status'])

                            if c.update_fields:
                                c.update_issue()
                            else:
                                c.add_comment('Unable to update comm status: ' + str(json.dumps(info.commStatus, indent=4)))

                            if info.invalidCommStatusFields:
                                c.add_comment(info.invalidCommStatusFields)
                    else:
                        jira.add_comment('Unable to link to %s Communications ticket' % c.get_p_key_from_info(info, tmp_link))
                else:
                    # Link to a specific ticket, if provided
                    to_key = tmp_link.upper()
                    jira.link_to(to_key)

                    if jira.result == 'Failed':
                        jira.add_comment('Unable to link to %s.' % to_key)

    # Add watchers if any
    if info.watchers:
        names = info.watchers.split(',')
        comment = ''
        for name in names:
            name = name.strip()
            jira.add_watcher(name)
            if jira.result != 'Failed':
                comment += 'Add watcher ' + name + '.\n'
            else:
                comment += 'Unable to add watcher ' + name + '.\n'
        if comment: jira.add_comment(comment, Security.none)

    # Add component if any
    if info.component:
        tmp_components = info.component.split(',')
        if tmp_components and len(tmp_components) > 0:
            for val in tmp_components:
                val = str(val).strip()
                if val.lower() in ('operations', 'implementation'):
                    val = val.capitalize()

                if val and val != "":
                    jira.add_component(val)
                    if jira.result == 'Failed':
                        jira.add_comment('Unable to add component %s' % val)

    return jira