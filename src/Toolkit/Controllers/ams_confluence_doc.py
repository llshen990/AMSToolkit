#!/usr/bin/env /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python
import argparse
import sys
import traceback
import os
import re
import time
import datetime
import cgi
import subprocess
import pwd
import six
import json
import logging
import requests
import urllib
import croniter
from cron_descriptor import get_description, ExpressionDescriptor, CasingTypeEnum
import StringIO
import xml.etree.ElementTree as et
import hashlib

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from Toolkit.Lib import AMSLogger
from Toolkit.Config import AMSConfig, AMSCommentable, AMSSchedule, AMSFileRoute, AMSFileParser, AMSFileHandler, AMSSecret
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Exceptions import AMSConfigException
from Toolkit.Thycotic import AMSSecretServer
from Toolkit.Lib.Helpers import Seconds2Time
from Toolkit.Models import AMSViya

# Compiled regex
re_reboot = re.compile('^@reboot')
re_number = re.compile('^[0-9\*\/\,-]+$')

err = []
months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
for x in range(12):
    months.append(str(x + 1).rjust(2, '0'))
weekdays = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
for x in range(7):
    weekdays.append(str(x).rjust(2, '0'))

TOOLKIT_TYPES = ['Schedule', 'File Route', 'File Parser', 'File Handler', 'Builtin', 'Data Management', 'Monitoring', 'Viya Flow']
CRONCMD = "/usr/bin/crontab"
ATCMD = "/usr/bin/at"
WORKSTREAMS_FILENAME = '/sso/sfw/ghusps-toolkit/ams-toolkit/workstreams.json'

# Only track an automation if it's frequency is < the threshold frequency
UPDATE_PAGE_THRESHOLD = datetime.timedelta(minutes=30)
def cleanse_text(text):
    if not text:
        return ''

    text = text.replace('\\', "\\\\")
    return cgi.escape(text)

def update_page(token, space_name, title, content):
    # curl -u roward:XXXXX -G "https://www.ondemand.sas.com/confluencedoc/rest/api/content/search" \
    # --data-urlencode "cql=space=JCPINT and title~'Automation Details' and type=page and label=etlops_automation" | python -mjson.tool
    #

    # curl -u roward:XXXXX -X POST -H 'Content-Type: application/json' -d '{"type":"page","title":"new page", "ancestors":[{"id":60038182}], "space":{"key":"TSTINT"},"body":{"storage":{"value":"<p>This is a new page</p>","representation":"storage"}}}' https://www.ondemand.sas.com/confluencedoc/rest/api/content/

    # Find the root AMS page
    search_url = ams_defaults.confluence_root + '/rest/api/content/search'
    content_url = ams_defaults.confluence_root + '/rest/api/content'

    try:
        search_title = title.replace('-', '')
        url = search_url+'?cql='+urllib.quote("space={} and title~'{}' and type=page and label=etlops_automation".format(space_name, search_title))
        ams_logger.info('Searching for page to update with title~{}: space_name={}'.format(search_title, space_name))

        response = requests.get(url,  headers = {'Authorization' : 'Basic {}'.format(token)})
        if not response.status_code == 200:
            ams_logger.error('Response status_code={} text={}'.format(response.status_code, response.text))
            raise Exception('Problem with Confluence query response')
        try:
            ams_logger.info('Successfully found page')
            ams_logger.debug('Successfully found page response={}'.format(response.text))
            value = json.loads(response.text)
        except Exception as e:
            value = []

        page_id = None
        page_title = None
        try:
            if len(value['results']) == 0:
                ams_logger.error('No result found for space={} and title={}:'.format(space_name, title))
            elif len(value['results']) == 1:
                page_id = value['results'][0]['id']
                page_title = value['results'][0]['title']
                ams_logger.info('Found id={} for page title={}'.format(page_id, title))
            else:
                ams_logger.error('More than one result found for space={} and title={}:'.format(space_name, title))
                for result in value['results']:
                    ams_logger.error('(id={}) {}{}: {}'.format(result['id'], ams_defaults.confluence_root, result['_links']['tinyui'], result['title']))
        except Exception as e:
            raise Exception('Exception raised looking for space={} and title~{}: {}'.format(space_name, title, e))

        # find the version of the existing page
        version = None
        try:
            url = content_url + '/' + page_id + '?expand=version'
            response = requests.get(url, headers={'Authorization' : 'Basic {}'.format(token), 'X-Atlassian-Token': 'no-check', 'Content-Type': 'application/json'})
            if response.status_code == 200:
                try:
                    value = json.loads(response.text)
                    version = value['version']['number']
                except Exception as e:
                    value = 0
            else:
                ams_logger.error('Response status_code={} text={}'.format(response.status_code, response.text))
                ams_logger.error('Problem looking for page id={}: url={}'.format(page_id, url))
        except Exception as e:
            ams_logger.error('Exception raised looking for page id={}: url={}'.format(page_id, url, e))

        if page_id is not None:
            # increment the version ... this is an int ... if it's not then it's not handled
            version = version + 1
            page_content = '{"id":"'+page_id+'", "type":"page", "title":"'+page_title+'", "space":{"key":"'+space_name+'"},"body":{"storage":{"value":"'+content+'","representation":"storage"}}, "version":{"number":'+str(version)+'}}'
            response = requests.put(content_url + '/' + page_id, data=page_content, headers={'Authorization' : 'Basic {}'.format(token), 'X-Atlassian-Token':'no-check', 'Content-Type':'application/json'})
            if response.status_code == 200:
                ams_logger.info('Successfully updated content on page id={}: url={}'.format(page_id, url))
            else:
                ams_logger.error('Response status_code={} text={}'.format(response.status_code, response.text))
                ams_logger.debug('Problem updating page with content\n{}\n'.format(page_content))
                raise Exception('Problem updating url={} title=\'{}\' in space={}'.format((content_url + '/' + page_id), page_title, space_name))
        else:
            raise Exception('No page_id found for space={} and title={}'.format(space_name, title))

    except Exception as e:
        logging.getLogger('AMS').error("Caught an exception running {}: {}".format(__file__, e))
        logging.getLogger('AMS').error("Traceback: " + traceback.format_exc())
        return None

def _test_month(month):
    if re_number.search(month):
        return True
    elif month in months:
        return True
    elif month[:3].upper() in months or month[:2] in months or month[:1].rjust(2, '0') in months:
        return True
    else:
        return False


def _test_weekday(weekday):
    if re_number.search(weekday):
        return True
    elif weekday in weekdays:
        return True
    elif weekday[:3].upper() in weekdays or weekday[:2] in weekdays or weekday[:1].rjust(2, '0') in weekdays:
        return True
    else:
        return False

def _number_or_infinity(number):
    if number == -1:
        return "Infinite"
    else:
        return number

def unscheduled_automations(item):
    out_file.write('<table class="wrapped"><tbody><tr><th>Name</th><th>Type</th></tr>\n')
    for i in item:
        out_file.write('<tr><td>{}</td><td>{}</td></tr>\n'.format(i[1], i[0]))
    out_file.write('</tbody></table>')


def generate_file_parsers(ams_config, output_header, priority, enabled):
    output = ''
    x = 0
    for parser in six.itervalues(ams_config.AMSFileParsers):
        parser = ams_config.get_file_parser_by_name(parser.file_parser_name)  # type: AMSFileParser
        if not parser.file_parser_name in enabled:
            unscheduled.append(('File Parser', parser.file_parser_name))
        if not args.all_automations and not parser.file_parser_name in enabled:
            continue
        output += '<ac:structured-macro ac:name="panel"><ac:rich-text-body>'
        output += generate_one_file_parser(parser, output_header)
        output += '</ac:rich-text-body></ac:structured-macro>\n'
        x += 1

    ams_logger.info('Generated {} File parsers'.format(x))
    return output

def generate_one_file_parser(parser, output_header):
    output = ''
    if output_header:
        output += '<h2>{}</h2>'.format(parser.file_parser_name)
    output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
    output += generate_commentable(parser, "File Parser")
    output += '<tr><th><pre>Directory</pre></th><td>{}</td></tr>'.format(parser.base_directory)
    output += '<tr><th><pre>File Pattern</pre></th><td>{}</td></tr>'.format(parser.file_pattern)
    output += '<tr><th><pre>Max Depth</pre></th><td>{}</td></tr>'.format(_number_or_infinity(parser.max_depth))
    output += '<tr><th><pre>Min Depth</pre></th><td>{}</td></tr>'.format(_number_or_infinity(parser.min_depth))
    output += '<tr><th><pre>Max Age</pre></th><td>{} days</td></tr>'.format(_number_or_infinity(parser.max_age))
    output += '<tr><th><pre>Search Pattern</pre></th><td>{}</td></tr>'.format(parser.search_pattern)
    output += '<tr><th><pre>Follow Symlinks</pre></th><td>{}</td></tr>'.format(parser.follow_symlinks)
    if parser.on_match_actions:
        output += '<tr><th><pre>Action</pre></th><td>{}</td></tr>'.format(parser.on_match_actions)
    if 'Zabbix' == parser.on_match_actions:
        assignee = "Project Owner"
        if parser.AMSJibbixOptions.assignee:
            assignee = parser.AMSJibbixOptions.get_final_assignee()
        output += '<tr><th><pre>Assignee</pre></th><td>{}</td></tr>'.format(assignee)
        if parser.AMSJibbixOptions.watchers:
            output += '<tr><th><pre>Watchers</pre></th><td>{}</td></tr>'.format(parser.AMSJibbixOptions.watchers)
        if parser.AMSJibbixOptions.labels:
            output += '<tr><th><pre>Labels</pre></th><td>{}</td></tr>'.format(parser.AMSJibbixOptions.labels)
        if parser.AMSJibbixOptions.component:
            output += '<tr><th><pre>Components</pre></th><td>{}</td></tr>'.format(parser.AMSJibbixOptions.component)
        comm = False
        other_ticket = False
        merge = False
        if parser.AMSJibbixOptions.link == 'comm':
            comm = True
        elif parser.AMSJibbixOptions.link and parser.AMSJibbixOptions.link != '':
            other_ticket = True
        if parser.AMSJibbixOptions.merge in ('Yes', 'yes', 'True', 'true'):
            merge = True
        integration_type = 'Ticket Creation'
        if comm:
            integration_type += ' with Communications ticket updates'
        elif other_ticket:
            integration_type += ' updating ' + parser.AMSJibbixOptions.link
        if merge:
            integration_type += 'and merge'
        output += '<tr><th><pre>JIRA Integration</pre></th><td>{}</td></tr>'.format(integration_type)
    else:
        if parser.parser_email_address:
            output += '<tr><th><pre>Email Recipient</pre></th><td>{}</td></tr>'.format(parser.parser_email_address)
        if parser.touch_file:
            output += '<tr><th><pre>Touch File</pre></th><td>{}</td></tr>'.format(parser.touch_file)
        if parser.clear_signal:
            output += '<tr><th><pre>Clear Signal</pre></th><td>{}</td></tr>'.format(parser.clear_signal)
        if parser.script:
            output += '<tr><th><pre>Script</pre></th><td>{}</td></tr>'.format(parser.script)

    output += '<tr><th><pre>Host</pre></th><td>{}</td></tr>'.format(parser.AMSJibbixOptions.host)
    output += '</tbody></table>'

    return output

def generate_overview(ams_config, config_file):
    output = ''
    output += '<ac:structured-macro ac:name="panel"><ac:rich-text-body>\n'
    output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>\n'
    output += '<tr><th><pre>Config File</pre></th><td>{}</td></tr>\n'.format(config_file)
    # check for viya auth setup
    auth_file = '/home/{}/.auth'.format(ams_config.run_user)
    if ams_config.viya_profile_name and FileExistsValidator.is_readable(auth_file):
        try:
            ams_viya = AMSViya(None, None, None, auth_file, ams_config.viya_profile_name)
            output += '<tr><th><pre>Viya Auth Profile</pre></th><td>{}</td></tr>\n'.format(ams_viya.profile)
            output += '<tr><th><pre>Viya URL</pre></th><td><a href="{}" target="null">{}</a></td></tr>\n'.format(ams_viya.base_url, ams_viya.base_url)
            output += '<tr><th><pre>Management VM</pre></th><td>{}</td></tr>\n'.format(ams_config.my_hostname)
        except Exception as e:
            ams_logger.warning('Problem with auth_file={}'.format(auth_file))
            ams_logger.warning('Exception={}'.str(e))
    else:
        output += '<tr><th><pre>Hostname</pre></th><td>{}</td></tr>\n'.format(ams_config.my_hostname)
    output += '<tr><th><pre>Run User</pre></th><td>{}</td></tr>\n'.format(ams_config.run_user)
    if time.tzname:
        output += '<tr><th><pre>Local Time Zone</pre></th><td>{}</td></tr>\n'.format(time.tzname[0])
    output += '<tr><th><pre>Zabbix Proxy</pre></th><td>{}</td></tr>\n'.format(ams_config.zabbix_proxy)
    output += '<tr><th><pre>Zabbix URL</pre></th><td><a target="_blank" href="{}/search.php?search={}">{}</a></td></tr>\n'.format(ams_config.zabbix_url, ams_config.my_hostname, ams_config.zabbix_url)
    output += '</tbody></table>\n'
    output += '</ac:rich-text-body></ac:structured-macro>\n'

    ams_logger.info('Generated Overview')
    return output


def generate_file_handlers(ams_config, output_header, priority, enabled):
    output = ''
    x = 0
    for handler in six.itervalues(ams_config.AMSFileHandlers):
        handler = ams_config.get_file_handler_by_name(handler.file_handler_name)  # type: AMSFileHandler
        if not handler.file_handler_name in enabled:
            unscheduled.append(('File Handler', handler.file_handler_name))
        if not args.all_automations and not handler.file_handler_name in enabled:
            continue
        output += '<ac:structured-macro ac:name="panel"><ac:rich-text-body>'
        output += generate_one_file_handler(handler, output_header)
        output += '</ac:rich-text-body></ac:structured-macro>\n'
        x += 1
    ams_logger.info('Generated {} File handlers'.format(x))
    return output

def generate_one_file_handler(handler, output_header):
    output = ''
    if output_header:
        output += '<h2>{}</h2>'.format(handler.file_handler_name)
    output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
    output += generate_commentable(handler, "File Handler")
    output += '<tr><th><pre>Directory</pre></th><td>{}</td></tr>'.format(handler.directory_to_watch)
    if handler.archive_directory:
        output += '<tr><th><pre>Archive Directory</pre></th><td>{}</td></tr>'.format(handler.archive_directory)
    output += '<tr><th><pre>File Pattern</pre></th><td>{}</td></tr>'.format(handler.file_pattern)
    output += '<tr><th><pre>Type</pre></th><td>{}</td></tr>'.format(handler.type)
    output += '<tr><th><pre>Level</pre></th><td>{}</td></tr>'.format(handler.level)
    output += '<tr><th><pre>Max Depth</pre></th><td>{}</td></tr>'.format(_number_or_infinity(handler.max_depth))
    output += '<tr><th><pre>Min Depth</pre></th><td>{}</td></tr>'.format(_number_or_infinity(handler.min_depth))
    output += '<tr><th><pre>Follow Symlinks</pre></th><td>{}</td></tr>'.format(handler.follow_symlinks)
    output += '<tr><th><pre>File Age</pre></th><td>{} days</td></tr>'.format(handler.file_age)

    output += '</tbody></table>'

    return output

def generate_file_routes(ams_config, output_header, priority, enabled):
    output = ''
    x = 0
    for route in six.itervalues(ams_config.AMSFileRoutes):
        route = ams_config.get_file_route_by_name(route.file_route_name)  # type: AMSFileRoute
        if not route.file_route_name in enabled:
            unscheduled.append(('File Route', route.file_route_name))
        if route.AMSJibbixOptions:
            if priority and route.AMSJibbixOptions.priority != priority:
                continue
            if not args.all_automations and not route.file_route_name in enabled:
                continue
        output += '<ac:structured-macro ac:name="panel"><ac:rich-text-body>'
        output += generate_one_file_route(route, output_header)
        output += '</ac:rich-text-body></ac:structured-macro>\n'
        x += 1

    ams_logger.info('Generated {} File routes'.format(x))
    return output

def generate_one_file_route(route, output_header, confluence=False):
    output = ''
    if output_header:
        output += '<h2>{}</h2>'.format(route.file_route_name)
    output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
    output += '<tr><th><pre>Type</pre></th><td>{}</td></tr>'.format(route.AMSFileRouteMethod.type)
    output += generate_commentable(route, "File Route")
    output += '<tr><th><pre>File Patterns</pre></th><td>{}</td></tr>'.format(str(route.AMSFileRouteMethod.file_patterns).replace(',',',<br/>'))
    output += '<tr><th><pre>From Directory</pre></th><td>{}</td></tr>'.format(route.AMSFileRouteMethod.from_directory)
    output += '<tr><th><pre>To Directory</pre></th><td>{}</td></tr>'.format(route.AMSFileRouteMethod.to_directory)
    output += '<tr><th><pre>Archive Directory</pre></th><td>{}</td></tr>'.format(route.AMSFileRouteMethod.archive_directory)

    output += generate_remote_host_details(route)

    if route.AMSJibbixOptions:
        assignee = "Project Owner"
        if route.AMSJibbixOptions.assignee:
            assignee = route.AMSJibbixOptions.get_final_assignee()
        output += '<tr><th><pre>Assignee</pre></th><td>{}</td></tr>'.format(assignee)
        if route.AMSJibbixOptions.watchers:
            output += '<tr><th><pre>Watchers</pre></th><td>{}</td></tr>'.format(route.AMSJibbixOptions.watchers)
        comm = False
        other_ticket = False
        if route.AMSJibbixOptions.link == 'comm':
            comm = True
        elif route.AMSJibbixOptions.link and route.AMSJibbixOptions.link != '':
            other_ticket = True
        integration_type = 'Ticket Creation'
        if comm:
            integration_type += ' with Communications ticket updates'
        elif other_ticket:
            integration_type += ' updating ' + route.AMSJibbixOptions.link
        output += '<tr><th><pre>JIRA Integration</pre></th><td>{}</td></tr>'.format(integration_type)
        output += '<tr><th><pre>Host</pre></th><td>{}</td></tr>'.format(route.AMSJibbixOptions.host)

    output += '</tbody></table>'

    output += generate_dependency_checks('Dependency Checks', route)

    output += '<p>Completion Handlers</p>'
    if route.AMSFileRouteMethod.on_success_handler_script:
        output += '<ul>'
        output += '<li><p>{}</p>'.format(route.AMSFileRouteMethod.on_success_handler_script)
        output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
        output += '</tbody></table></li>'
        output += '</ul>\n'
    else:
        output += '<ul><li>None</li></ul>'

    return output


def generate_remote_host_details(route):
    output = ''
    if route.AMSFileRouteMethod.type in ('SftpPull', 'SftpPush'):
        if route.AMSFileRouteMethod.host:
            output += '<tr><th><pre>SFT host</pre></th><td>{}</td></tr>'.format(route.AMSFileRouteMethod.host)
        if route.AMSFileRouteMethod.port:
            output += '<tr><th><pre>SFTP port</pre></th><td>{}</td></tr>'.format(route.AMSFileRouteMethod.port)

    elif route.AMSFileRouteMethod.type in ('ADLSPull', 'ADLSPush'):
        if route.AMSFileRouteMethod.tenant:
            output += '<tr><th><pre>Tenant</pre></th><td>{}</td></tr>'.format(route.AMSFileRouteMethod.tenant)
        if route.AMSFileRouteMethod.client_id:
            output += '<tr><th><pre>Client ID</pre></th><td>{}</td></tr>'.format(route.AMSFileRouteMethod.client_id)
        if route.AMSFileRouteMethod.client_secret:
            output += '<tr><th><pre>Client Secret</pre></th><td>{}</td></tr>'.format("Please check on the host machine for details")
        if route.AMSFileRouteMethod.store_name:
            output += '<tr><th><pre>Store Name</pre></th><td>{}</td></tr>'.format(route.AMSFileRouteMethod.store_name)

    elif route.AMSFileRouteMethod.type in ('S3Pull', 'S3Push'):
        if route.AMSFileRouteMethod.s3_default_bucket:
            output += '<tr><th><pre>S3 Default Bucket</pre></th><td>{}</td></tr>'.format(route.AMSFileRouteMethod.s3_default_bucket)

    else:
        pass

    return output


def generate_commentable(commentable, type_of_commentable):
    output = ''
    if commentable.confluence_comment:
        output += '<tr><th><pre>Description</pre></th><td><pre>{}</pre></td></tr>'.format(commentable.confluence_comment)
    if commentable.details:
        output += '<tr><th><pre>JIRA Details</pre></th><td><pre>{}</pre></td></tr>'.format(commentable.details)
    if commentable.runbook_sub_link:
        output = '<tr><th><pre>Handling Issues</pre></th><td><pre><a target="_blank" href="{}">Runbook link on handling specific issues for this {}.</a></pre></td></tr>'.format(cleanse_text(commentable.runbook_sub_link), type_of_commentable)
    return output

def generate_dependency_checks(title, thing):
    output = ''
    output += '<p>{}</p>'.format(title)
    if thing and thing.AMSDependencyChecks:

        if hasattr(thing, 'AMSDependencyJibbixOptions') and thing.AMSDependencyJibbixOptions:
            output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
            output += '<tr><th><pre>Dependency Priority</pre></th><td>{}</td></tr>'.format(thing.AMSDependencyJibbixOptions.priority)

            assignee = "Project Owner"
            if thing.AMSDependencyJibbixOptions.assignee:
                assignee = thing.AMSDependencyJibbixOptions.get_final_assignee()
            output += '<tr><th><pre>Dependency Assignee</pre></th><td>{}</td></tr>'.format(assignee)
            if thing.AMSDependencyJibbixOptions.watchers:
                output += '<tr><th><pre>Dependency Watchers</pre></th><td>{}</td></tr>'.format(thing.AMSDependencyJibbixOptions.watchers)
            if thing.AMSDependencyJibbixOptions.labels:
                output += '<tr><th><pre>Dependency Labels</pre></th><td>{}</td></tr>'.format(thing.AMSDependencyJibbixOptions.labels)
            if thing.AMSDependencyJibbixOptions.component:
                output += '<tr><th><pre>Dependency Components</pre></th><td>{}</td></tr>'.format(thing.AMSDependencyJibbixOptions.component)
            comm = False
            merge = False
            other_ticket = False
            if thing.AMSDependencyJibbixOptions.link == 'comm':
                comm = True
            elif thing.AMSDependencyJibbixOptions.link and thing.AMSDependencyJibbixOptions.link != '':
                other_ticket = True
            integration_type = 'Ticket Creation'
            if thing.AMSJibbixOptions.merge in ('Yes', 'yes', 'True', 'true'):
                merge = True
            if comm:
                integration_type += ' with Communications ticket updates'
            elif other_ticket:
                integration_type += ' updating ' + thing.AMSDependencyJibbixOptions.link
            if merge:
                integration_type += ', merge '
            if not comm:
                integration_type += ' to the Communications ticket'
            output += '<tr><th><pre>Dependency JIRA Integration</pre></th><td>{}</td></tr>'.format(integration_type)
            output += '</tbody></table>'

        output += '<ul>'
        for dependency in six.itervalues(thing.AMSDependencyChecks):
            output += '<li><p>{}</p>'.format(dependency.dependency_check_name)
            output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
            output += '<tr><th><pre>Type</pre></th><td><pre><a target="_blank" href="https://sasoffice365.sharepoint.com/sites/MASETLOperations/SitePages/AMP---Handling-Issues.aspx#{}">{}</a></pre></td></tr>'.format(str(dependency.type).lower(), dependency.type)
            # If this is a file Dependency then separate the list with breaks based on the ,
            index = 0
            try:
                index = str(dependency.type).index('File')
            except Exception as e:
                pass
            if index >= 0:
                output += '<tr><th><pre>Dependency</pre></th><td><pre>{}</pre></td></tr>'.format(str(dependency.dependency).replace(',',',<br/>'))
            else:
                output += '<tr><th><pre>Dependency</pre></th><td><pre>{}</pre></td></tr>'.format(dependency.dependency)
            if dependency.max_attempts == 1:
                output += '<tr><th><pre>Max Attempts</pre></th><td><pre>Once</pre></td></tr>'
            else:
                output += '<tr><th><pre>Max Attempts</pre></th><td><pre>{}</pre></td></tr>'.format(dependency.max_attempts)
                output += '<tr><th><pre>Attempt Interval</pre></th><td><pre>{}</pre></td></tr>'.format(Seconds2Time(dependency.attempt_interval).convert2readable())
            output += generate_commentable(dependency, 'Dependency Check')
            output += '</tbody></table></li>'
        output += '</ul>\n'
    else:
        output += '<ul><li>None</li></ul>'

    return output


def generate_complete_handler(title, thing):
    output = '<p>{}</p>'.format(title)
    if thing:
        output += '<ul>'
        for handler in six.itervalues(thing):
            output += '<li><p>{}</p>'.format(handler.complete_handler_name)
            output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
            output += '<tr><th><pre>Type</pre></th><td><pre><a target="_blank" href="https://sasoffice365.sharepoint.com/sites/MASETLOperations/SitePages/AMP---Handling-Issues.aspx#{}">{}</a></pre></td></tr>'.format(str(handler.type).lower(), handler.type)
            output += generate_commentable(handler, "Complete Handler")
            if handler.complete_handler:
                output += '<tr><th><pre>Parameter</pre></th><td><pre>{}</pre></td></tr>'.format(handler.complete_handler)
            if handler.service_params:
                output += '<tr><th><pre>Parameters</pre></th><td><pre>{}</pre></td></tr>'.format(json.dumps(handler.service_params, indent=2, separators=(',', ': ')))
            output += '</tbody></table></li>'
        output += '</ul>\n'
    else:
        output += '<ul><li>None</li></ul>'

    return output


def generate_one_viya_flow(ams_viya, flow_json, output_header=True, confluence=False):
    output = ''
    name = cleanse_text(flow_json['name'])
    if output_header:
        output += '<h2>{}</h2>'.format(name)
    output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
    if 'description' in flow_json:
        description = flow_json['description']
    else:
        description = '<None>'
    output += '<tr><th><pre>Description</pre></th><td>{}</td></tr>'.format(cleanse_text(description))
    output += '<tr><th><pre>Created By</pre></th><td>{}</td></tr>'.format(cleanse_text(flow_json['createdBy']))
    output += '<tr><th><pre>Created</pre></th><td>{}</td></tr>'.format(cleanse_text(flow_json['creationTimeStamp']))
    output += '<tr><th><pre>Id</pre></th><td>{}</td></tr>'.format(cleanse_text(flow_json['id']))
    output += '</tbody></table>'

    if 'jobs' in flow_json:
        output += "<p/>"
        if confluence:
            output += '<ac:structured-macro ac:name="expand" ac:schema-version="1"><ac:parameter ac:name="title">Configured Jobs</ac:parameter><ac:rich-text-body>'
        else:
            output += '<details><summary>Configured Jobs</summary>'

        for job_uri in flow_json['jobs']:
            job = ams_viya.list_flow_job(uuid=job_uri.split('/')[3])
            job_text = job['name']
            output += '<ul><li>{}</li></ul>'.format(cleanse_text(job_text))

        if confluence:
            output += '</ac:rich-text-body></ac:structured-macro>\n\n'
        else:
            output += '</details>'

    if 'dependencies' in flow_json:
        if confluence:
            output += '<ac:structured-macro ac:name="expand" ac:schema-version="1"><ac:parameter ac:name="title">Dependencies</ac:parameter><ac:rich-text-body>'
        else:
            output += '<details><summary>Dependencies</summary>'

        for dependency in flow_json['dependencies']:
            output += '<ul><li>{}</li>'.format(cleanse_text(dependency['target']))
            output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
            if 'event' in dependency:
                output += '<tr><th><pre>Type</pre></th><td>{}</td></tr>'.format(cleanse_text(dependency['event']['type']))
                output += '<tr><th><pre>Expression</pre></th><td>{}</td></tr>'.format(cleanse_text(dependency['event']['expression']))
            output += '</tbody></table></ul>'
            output += "<p/>"

        if confluence:
            output += '</ac:rich-text-body></ac:structured-macro>\n\n'
        else:
            output += '</details>'

    return output


def generate_viya_flows(auth_file, config, output_header=True):
    output = ''
    x = 0

    ams_viya = AMSViya(None, None, None, auth_file, config.viya_profile_name)
    if config.viya_flow_ids:
        flows = ams_viya.list_flows(uuid=config.viya_flow_ids)
    else:
        flows = ams_viya.list_flows(user=config.run_user)

    if flows and 'count' in flows:
        ams_logger.info("Found {} flows".format(flows['count']))
        for item in flows['items']:
            try:
                output += '<ac:structured-macro ac:name="panel"><ac:rich-text-body>'
                output += generate_one_viya_flow(ams_viya, item, output_header, True)
                output += '</ac:rich-text-body></ac:structured-macro>\n'
                x += 1
            except Exception as e:
                ams_logger.warning('Problem with flow={}'.format(item))
                ams_logger.warning("Traceback: " + traceback.format_exc())
                ams_logger.warning('Exception={}'.str(e))

    ams_logger.info('Generated {} Viya Flows'.format(x))
    return output


def generate_schedules(ams_config, project, output_header, priority, enabled):
    output = ''
    x = 0
    found_project = None
    if project:
        if project in ams_config.AMSProjects:
            found_project = ams_config.AMSProjects[project]
        else:
            raise Exception('No project {} found in config'.format(project))

    if len(ams_config.AMSProjects)>0:
        found_project = ams_config.AMSProjects.values()[0]
        ams_logger.info('Generating schedules based from project {} in config'.format(found_project.project_name))

    if found_project:
        for name in six.itervalues(found_project.AMSSchedules):
            schedule = ams_config.get_schedule_by_name(name.schedule_name)  # type: AMSSchedule
            if not schedule.schedule_name in enabled:
                unscheduled.append(('Schedule', schedule.schedule_name))
            if priority and schedule.AMSJibbixOptions.priority != priority:
                continue
            if not args.all_automations and not schedule.schedule_name in enabled:
                continue
            output += '<ac:structured-macro ac:name="panel"><ac:rich-text-body>'
            output += generate_one_schedule(schedule, output_header, True)
            output += '</ac:rich-text-body></ac:structured-macro>\n'
            x += 1

    ams_logger.info('Generated {} Schedules'.format(x))
    return output

def generate_one_schedule(schedule, output_header, confluence=False):
    output = ''
    # find entry if available
    crontab_entry = None
    if schedule.schedule_name in enabled:
        crontab_entry = enabled[schedule.schedule_name]
    if schedule.AMSJibbixOptions is None:
        schedule.AMSJibbixOptions = AMSDefaults().AMSJibbixOptions
    if output_header:
        output += '<h2>{}</h2>'.format(schedule.schedule_name)
    output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
    output += '<tr><th><pre>Type</pre></th><td>{}</td></tr>'.format(schedule.automation_type)
    output += '<tr><th><pre>Home Dir</pre></th><td>{}</td></tr>'.format(schedule.home_dir)
    output += '<tr><th><pre>Priority</pre></th><td>{}</td></tr>'.format(schedule.AMSJibbixOptions.priority)
    if schedule.longtime:
        output += '<tr><th><pre>Longtime</pre></th><td>{}</td></tr>'.format(schedule.longtime)
    if schedule.longtime_priority:
        output += '<tr><th><pre>Longtime Priority</pre></th><td>{}</td></tr>'.format(schedule.longtime_priority)
    if schedule.shorttime:
        output += '<tr><th><pre>Shorttime</pre></th><td>{}</td></tr>'.format(schedule.shorttime)
    if crontab_entry and crontab_entry['trigger']:
        output += '<tr><th><pre>Trigger</pre></th><td>{}</td></tr>'.format(crontab_entry['trigger'])

    assignee = "Project Owner"
    if schedule.AMSJibbixOptions.assignee:
        assignee = schedule.AMSJibbixOptions.get_final_assignee()
    output += '<tr><th><pre>Assignee</pre></th><td>{}</td></tr>'.format(assignee)
    if schedule.AMSJibbixOptions.watchers:
        output += '<tr><th><pre>Watchers</pre></th><td>{}</td></tr>'.format(schedule.AMSJibbixOptions.watchers)
    if schedule.AMSJibbixOptions.labels:
        output += '<tr><th><pre>Labels</pre></th><td>{}</td></tr>'.format(schedule.AMSJibbixOptions.labels)
    if schedule.AMSJibbixOptions.component:
        output += '<tr><th><pre>Components</pre></th><td>{}</td></tr>'.format(schedule.AMSJibbixOptions.component)
    comm = False
    other_ticket = False
    start_stop = False
    stats = False
    merge = False
    if schedule.AMSJibbixOptions.link == 'comm':
        comm = True
    elif schedule.AMSJibbixOptions.link and schedule.AMSJibbixOptions.link != '':
        other_ticket = True
    if schedule.schedule_update_comment_link:
        stats = True
    if schedule.AMSJibbixOptions.merge in ('Yes', 'yes', 'True', 'true'):
        merge = True
    if schedule.start_stop_comment_link:
        start_stop = True
    integration_type = 'Ticket Creation'
    if comm:
        integration_type += ' with Communications ticket updates'
    elif other_ticket:
        integration_type += ' updating ' + schedule.AMSJibbixOptions.link
    if start_stop:
        integration_type += ', start/stop comments '
    if merge:
        integration_type += ', merge '
    if stats:
        integration_type += ' and stats'
    if not comm and stats:
        integration_type += ' to the Communications ticket'
    output += '<tr><th><pre>JIRA Integration</pre></th><td>{}</td></tr>'.format(integration_type)
    if schedule.AMSJibbixOptions.host:
        output += '<tr><th><pre>Host</pre></th><td>{}</td></tr>'.format(schedule.AMSJibbixOptions.host)
    if schedule.AMSDependencyChecks:
        output += '<tr><th><pre>Dependency Policy</pre></th><td>{}</td></tr>'.format(schedule.dependency_check_policy)
    output += '</tbody></table>'
    output += '<p>Action on schedule failure</p><ul><li>'
    output += 'Check runbook section on "<a target="_blank" href="'
    if schedule.runbook_sub_link:
        output += cleanse_text(schedule.runbook_sub_link)
    else:
        output += '#HandlingIssues'
    output += '">Handling issues</a>"'
    output += '</li></ul>'
    if schedule.confluence_comment:
        output += '<p>Additional details:</p>'.format(schedule.confluence_comment)
        for line in str(schedule.confluence_comment).split('\n'):
            output += '<ul><li>{}</li></ul>'.format(line)

    output += generate_dependency_checks('Dependency Checks', schedule)
    output += generate_complete_handler('Success Complete Handlers', schedule.AMSSuccessCompleteHandler)
    output += generate_complete_handler('Error Complete Handlers', schedule.AMSErrorCompleteHandler)

    # add collapsible tree of the job structure
    if schedule.automation_type in ('SSORun', 'Sked'):
        try:
            with open(schedule.schedule_name, "r") as schedule_file:
                tree = et.parse(schedule_file)

                job_text = "<p/>"
                if confluence:
                    job_text += '<ac:structured-macro ac:name="expand" ac:schema-version="1"><ac:parameter ac:name="title">Configured {} Jobs</ac:parameter><ac:rich-text-body>'.format(schedule.automation_type)
                else:
                    job_text += '<details><summary>Configured {} Jobs</summary>'.format(schedule.automation_type)

                job_text += generate_jobs(tree.getroot())
                if confluence:
                    job_text += '</ac:rich-text-body></ac:structured-macro>\n\n'
                else:
                    job_text += '</details>'
                output += job_text
        except Exception as e:
            ams_logger.warning('Cannot generate XML structure for {}'.format(schedule.schedule_name))

    return output

def generate_secrets(ams_config, output_header):
    output = ''
    x = 0
    for secret in six.itervalues(ams_config.AMSSecrets):
        secret = ams_config.get_secret_by_name(secret.secret_name)  # type: AMSSecret
        output += '<ac:structured-macro ac:name="panel"><ac:rich-text-body>'
        output += generate_one_secret(ams_config, secret, output_header)
        output += '</ac:rich-text-body></ac:structured-macro>\n'
        x += 1
    if x == 0:
        out_file.write('<p>None</p>\n\n')

    ams_logger.info('Generated {} Secrets'.format(x))
    return output

def generate_one_secret(ams_config, secret, output_header):
    output = ''
    if output_header:
        output += '<h2>{}</h2>'.format(secret.secret_name)
    output += '<table class="wrapped"><colgroup><col/><col/></colgroup><tbody>'
    href = 'https://securevault.sas.com/secretserver/app/#/secret/{}/general'.format(secret.secret_id)
    output += '<tr><th><pre>Secret ID</pre></th><td><a href="{}">{}</a></td></tr>'.format(href, secret.secret_id)
    username = 'Unknown'
    try:
        username = ams_config.decrypt(secret.username)
    except Exception as e:
        pass
    output += '<tr><th><pre>Username</pre></th><td>{}</td></tr>'.format(username)
    if secret.domain:
        output += '<tr><th><pre>Domain</pre></th><td>{}</td></tr>'.format(secret.domain)
    if secret.https_proxy:
        output += '<tr><th><pre>Proxy</pre></th><td>{}</td></tr>'.format(secret.https_proxy)

    output += '</tbody></table>'

    return output

def get_element_or_empty(element, field):
    result = ''
    try:
        value = cleanse_text(element.get(field))
        if value:
            result = '{}={}'.format(field, value)
    except Exception as e:
        pass
    return result

def generate_jobs(root):
    output = ''
    if len(root):
        for child in root.findall('entry'):
            output += '<ul><li>'
            depend = 'None'
            try:
                depend = cleanse_text(child.findall('depend')[0].text)
            except Exception as e:
                pass
            output += '<b>{}</b>'.format(cleanse_text(child.get('name')))
            output += '<ul><li>type={}</li></ul>'.format(cleanse_text(child.get('type')))
            output += '<ul><li>file={}</li></ul>'.format(cleanse_text(child.get('file')))
            output += '<ul><li>depend={}</li></ul>'.format(depend)
            output += '</li></ul>'
    return output

def get_parameter_from_line(line, parameter):
    try:
        begin = line.index(parameter)
        end = begin + len(parameter)
        has_quotes = False
        # skip over any whitespace
        while line[end] and (line[end] in ['=', ' ', '"']):
            x = line[end]
            end += 1
            if line[end-1] == '"':
                has_quotes = True
                begin += 1
                while line[end] != '"':
                    end += 1
                break
        try:
            if not has_quotes:
                end = line.index(' ', end)
        except ValueError:
            end = len(line)
        length = len(parameter)
        if parameter in line:
            length += 1
        return line[begin+length:end].strip(';')
    except Exception as e:
        return 'None'

def get_command(at_cmd, job_no):
    try:
        out = subprocess.check_output([at_cmd, '-c', job_no], universal_newlines=True)

        if 'marcinDELIMITER' in out:
            regex_match = re.compile('''\n}\n.*?\s.*(?P<command>\s.*)''')
        else:
            regex_match = re.compile('''\n}\n(?P<command>.*)''')

        return regex_match.search(out).group('command').strip()
    except Exception as e:
        print e
        return ""

def parse_automation_type(entry, line):
    if 'sso_batch' in entry['job']:
        entry['type'] = 'sso_batch'
    elif 'sso_nightly' in entry['job']:
        entry['type'] = 'sso_nightly'
    elif 'sso_run_error_check.py' in entry['job']:
        entry['type'] = 'Monitoring'
    elif 'flow_trigger_monitoring' in entry['job']:
        entry['type'] = 'Monitoring'
        runuser = get_parameter_from_line(line, '-p')
        entry['automation_name'] = 'Viya Job Monitoring ({})'.format(runuser)
    elif 'ams_schedule_launcher' in entry['job']:
        entry['type'] = 'Schedule'
        if '--schedule' in entry['job']:
            entry['automation_name'] = get_parameter_from_line(line, '--schedule_name')
            if entry['automation_name'] == 'None':
                entry['automation_name'] = get_parameter_from_line(line, '--schedule')
        if '--trigger_script' in entry['job']:
            entry['trigger'] = get_parameter_from_line(line, '--trigger_script')
        if '--trigger_file' in entry['job']:
            entry['trigger'] = get_parameter_from_line(line, '--trigger_file')
    elif 'ams_encryption_handler' in entry['job']:
        action = get_parameter_from_line(line, '--action')
        type = get_parameter_from_line(line, '--type')
        if type == 'None':
            type = 'PGP'
        entry['type'] = 'Data Management'
        entry['automation_name'] = '{} {}'.format(type, action)
    elif 'ams_route_files' in entry['job']:
        entry['type'] = 'File Route'
        entry['automation_name'] = get_parameter_from_line(line, '--file_route_name')
        if entry['automation_name'] == 'None':
            entry['automation_name'] = get_parameter_from_line(line, '--file_route')
    elif 'ams_file_parser' in entry['job']:
        entry['type'] = 'File Parser'
        entry['automation_name'] = get_parameter_from_line(line, '--file_parser_name')
        if entry['automation_name'] == 'None':
            entry['automation_name'] = get_parameter_from_line(line, '--file_parser')
    elif 'ams_file_handler' in entry['job']:
        entry['type'] = 'File Handler'
        entry['automation_name'] = get_parameter_from_line(line, '--file_handler_name')
        if entry['automation_name'] == 'None':
            entry['automation_name'] = get_parameter_from_line(line, '--file_handler')
    elif 'smoketest' in entry['job']:
        entry['type'] = 'Builtin'
        param = get_parameter_from_line(line, '--service')
        if param != 'None':
            entry['automation_name'] = 'Smoke Test for ' + param
        else:
            entry['automation_name'] = 'Smoke Test'
    elif 'ams_confluence_doc' in entry['job']:
        entry['type'] = 'Builtin'
        param = get_parameter_from_line(line, '--project')
        if param != 'None':
            entry['automation_name'] = 'Documentation Generation for ' + param
        else:
            entry['automation_name'] = 'Documentation Generation'
    elif 'crontab_backup.sh' in entry['job']:
        entry['type'] = 'Builtin'
        entry['automation_name'] = 'Crontab Backup'
    elif 'ams_source_control_manager' in entry['job']:
        entry['type'] = 'Builtin'
        entry['automation_name'] = 'Source Control Status'
    else:
        entry['automation_name'] = line
        entry['type'] = 'other'

    return entry

def parse_cron(line):
    entry = {
        'minute': '',
        'hour': '',
        'day': '',
        'month': '',
        'weekday': '',
        'special': '',
        'job': '',
        'adhoc': '',
        'valid': '',
        'trigger': '',
        'calculated_day': 0
    }
    if line.startswith('#') or len(line) == 0:
        return None
    explode = line.split()
    valid = True
    adhoc = False
    if len(explode) > 1:
        if re_reboot.search(explode[0]):
            entry['special'] = '@reboot'
            valid = True
        elif len(explode) >= 6:
            minute = explode[0]
            hour = explode[1]
            day = explode[2]
            month = explode[3]
            weekday = explode[4]
            if not re_number.search(minute):
                valid = False
            if not re_number.search(hour):
                valid = False
            if not re_number.search(day):
                valid = False
            if not _test_month(month):
                valid = False
            if not _test_weekday(weekday):
                valid = False
            if '/sso/sfw/ghusps-toolkit/ams-toolkit/config/default/adhoc_crontab.sh' in line:
                adhoc = False
            elif valid and minute != '*' and hour != '*' and day != '*' and month != '*' and 'adhoc' in line.lower():
                adhoc = True
        else:
            valid = False
    else:
        valid = False

    entry['valid'] = valid
    entry['adhoc'] = adhoc
    entry['scheduler'] = 'cron'
    if not valid:
        entry['job'] = line
    else:
        entry['minute'] = minute
        entry['hour'] = hour
        entry['day'] = day
        entry['month'] = month
        entry['weekday'] = weekday
        entry['automation_name'] = ''
        entry['job'] = ' '.join(explode[5:])
        entry['crontime'] = minute + " " + hour + " " + day + " " + month + " " + weekday
        match = re.match('.*(\\$*\(date.*\&\&)', entry['job'])
        # detect date manipulation in crontab line
        if match:
            special = entry['job'][:entry['job'].index('&&')].strip()
            if (special.startswith('[') and special.endswith(']')) or (special.startswith('(') and special.endswith(')')):
                special = special[1:-1].strip()
            entry['special'] = special


        # adjust non-standard 'every day' and '7' for Sunday
        if weekday == '1-7':
            weekday = '0-6'
        elif weekday == '7':
            weekday = '0'
        try:
            entry['description'] = ExpressionDescriptor(minute + " " + hour + " " + day + " " + month + " " + weekday, casing_type=CasingTypeEnum.Sentence, use_24hour_time_format=True).get_description()
        except Exception:
            ams_logger.warning('Expression "{}" is not supported by cron_descriptor'.format(entry['crontime']))
            entry['description'] = minute + " " + hour + " " + day + " " + month + " " + weekday
        entry['calculated_day'] = calculate_day(entry)

    parse_automation_type(entry, line)

    entry['next_scheduled'] = get_next_execution(explode[:5],entry['type'])

    return entry

def calculate_day(entry):
    if entry['weekday'] != '*':
        x = entry['weekday']
        if len(x) == 1:
            return 'AAA' + entry['weekday']
        else:
            return 'ZZA' + entry['weekday']
    elif entry['day'] != '*':
        return 'ZZB' + entry['day']
    else:
        return 'ZZZ'

def get_next_execution(expression,automation_type):
    if automation_type != "Schedule":
        return "Not Tracked"
    expression = " ".join(expression)
    now = datetime.datetime.now()
    try:
        # Get next execution
        cron = croniter.croniter(expression, now)
        next_execution = cron.get_next(datetime.datetime)
        # Get next-next execution to compare frequency to update page threshold
        next_next_execution = cron.get_next(datetime.datetime)
        difference = next_next_execution - next_execution
        if difference <= UPDATE_PAGE_THRESHOLD:
            ams_logger.info("Automation runs more frequently than threshold so not tracked")
            return "Not Tracked"
    except Exception as e:
        ams_logger.error("Error calculating next execution of cron expression: '{}', {}".format(expression,e))
        return "Not Tracked"
    return next_execution

def hash_changed(out_file,schedule_details):
    old_hash = None
    # Compare existing schedule details file on disk's hash to the new schedule details in memory
    if os.path.exists(schedule_details):
        with open(schedule_details, "r") as f:
            data = f.read()
            old_hash = hashlib.md5(data).hexdigest()
    new_hash = hashlib.md5(str(out_file.getvalue())).hexdigest()
    if new_hash == old_hash:
        ams_logger.info("Hash not changed")
    else:
        ams_logger.info("Hash changed")
    return True if new_hash != old_hash else False

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

if __name__ == "__main__":
    try:
        arg_parser = argparse.ArgumentParser()
        # noinspection PyTypeChecker
        arg_parser.add_argument("--config_file", nargs='?', type=str, help="Config File", required=True)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--crontab_file", nargs='?', type=str, help="Crontab File", required=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--output_file", nargs='?', type=str, help="Output File", required=False, default='schedule-details.html')
        # noinspection PyTypeChecker
        arg_parser.add_argument("--project", nargs='?', type=str, help="Project", required=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--priority", nargs='?', type=str, help="Priority", required=False, default=None)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--all_automations", nargs='?', type=lambda x: bool(str2bool(x)), default=False, const=True, help="All Automations", required=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--generate_confluence", nargs='?', type=lambda x: bool(str2bool(x)), default=False, const=True, help="Generate a Confluence Page", required=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--confluence_title", nargs='?', type=str, help="Confluence page title to update (defaults to Automation Details - {PROJECT})", default=None, required=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--force", nargs='?', type=lambda x: bool(str2bool(x)), default=False, const=True, help="Force generation of Confluence Page", required=False)

        args = arg_parser.parse_args(sys.argv[1:])

        ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
        ams_defaults = AMSDefaults()

        ams_config = []

        import glob
        if args.config_file:
            config_list = glob.glob(args.config_file)
            for l in config_list:
                config = AMSConfig(str(l).strip())
                ams_logger.set_debug(config.debug)
                if not config.valid_config:
                    raise AMSConfigException('Invalid configuration file specified: %s' % args.config_file)
                ams_config.append(config)

        if args.priority:
            priority = args.priority.strip()
        else:
            priority = None

        ams_logger.info('Using priority {}'.format(priority))

        output_file = args.output_file.strip()
        ams_logger.info('Outputting HTML to file {}'.format(os.path.join(os.getcwd(), output_file)))

        out_file = StringIO.StringIO()
        try:
            tla = ams_config[0].get_my_environment().tla
        except:
            tla = "NONE"

        # read the crontab file
        contents = ''
        if args.crontab_file:
            ams_logger.info('Reading crontab from file {}'.format(args.crontab_file))
            contents = open(str(args.crontab_file).strip()).read()
        else:
            ams_logger.info('Reading crontab of user {}'.format(pwd.getpwuid(os.getuid())[0]))
            try:
                contents = subprocess.check_output([CRONCMD, '-l'], universal_newlines=True)
            except Exception as e:
                ams_logger.error("Problem with crontab={}".format(e))
        unparsed = [line.strip() for line in contents.strip().split('\n')]
        timestamp = str(time.time())
        entries = []
        for line in unparsed:
            entry = parse_cron(line)
            if entry:
                entries.append(entry)

        # look in atq also for entries
        try:
            contents = subprocess.check_output([ATCMD, '-l'], universal_newlines=True)
            ams_logger.info("At found these jobs={}".format(contents))

            keys = ['job_no', 'day', 'month', 'day_of_month', 'time', 'year', 'queue', 'user']
            for job in contents.splitlines():
                try:
                    _job = dict(zip(keys, job.split()))
                    _job['scheduler'] = 'at'
                    _job['valid'] = True
                    _job['adhoc'] = True
                    _job['description'] = 'At {} on {} {} {}'.format(_job['time'], _job['day_of_month'], _job['month'], _job['year'])
                    _job['calculated_day'] = _job['day_of_month']
                    _job['next_scheduled'] = 'Not Tracked'
                    _job['job'] = get_command(ATCMD, _job.get('job_no'))
                    ams_logger.debug("Parsing job_no={}".format(_job.get('job_no')))
                    parse_automation_type(_job, _job['job'])
                    ams_logger.info("Adding parsed job={}".format(_job))
                    entries.append(_job)
                except Exception as e:
                    ams_logger.error("Problem with job entry={}".format(e))

        except Exception as e:
            ams_logger.error("Problem with atcmd={}".format(e))

        # sort the entries
        import operator

        entries.sort(key=operator.itemgetter('calculated_day'), reverse=False)

        out_file.write('<h1>Overview</h1>')
        out_file.write(generate_overview(config, config.config_path))
        out_file.write('<br/>')
        need_overview = False

        out_file.write(
            '<ac:structured-macro ac:name="multiexcerpt-enhanced-permissions">\n<ac:parameter ac:name="GroupsAllowedToViewAnywhere">{} Jira - Confluence</ac:parameter>\n<ac:parameter ac:name="MultiExcerptName">full-content</ac:parameter>\n<ac:parameter '
            'ac:name="atlassian-macro-output-type">INLINE</ac:parameter>\n<ac:rich-text-body>\n\n'.format(tla))
        out_file.write('<ac:structured-macro ac:name="toc"><ac:parameter ac:name="maxLevel">2</ac:parameter><ac:parameter ac:name="exclude">Overview</ac:parameter></ac:structured-macro>\n\n')

        enabled = {}
        unscheduled = []
        configured_automations = []

        # Generate Viya flows if configured
        auth_file = '/home/{}/.auth'.format(config.run_user)
        if config.viya_profile_name and FileExistsValidator.is_readable(auth_file):
            ams_viya = AMSViya(None, None, None, auth_file, config.viya_profile_name)
            if config.viya_flow_ids:
                flows = ams_viya.list_flows(uuid=config.viya_flow_ids)
            else:
                flows = ams_viya.list_flows(user=config.run_user)
            if flows and 'count' in flows:
                ams_logger.info("Found {} flows".format(flows['count']))
                for item in flows['items']:
                    try:
                        name = item['name']
                        if 'description' in item:
                            description = item['description']
                        else:
                            description = '<None>'
                        flowid = item['id']
                        triggers = None
                        if 'triggers' in item:
                            triggers = item['triggers']
                        new_flow = {'automation_name': name, 'type': 'Viya Flow', 'scheduler': 'Viya', 'valid': True,
                                    'adhoc': False, 'special': False}
                        trigger_text = str(triggers)
                        if triggers:
                            first_trigger = triggers[0]
                            if 'name' in first_trigger:
                                trigger_text = first_trigger['name']
                            if 'event' in first_trigger and 'name' in first_trigger['event']:
                                trigger_text = first_trigger['event']['name']
                        new_flow['description'] = trigger_text
                        new_flow['calculated_day'] = ''
                        new_flow['next_scheduled'] = 'Not Tracked'
                        entries.append(new_flow)
                        configured_automations.append(name)
                    except Exception as e:
                        ams_logger.warning('Problem with flow={}'.format(item))
                        ams_logger.warning("Traceback: " + traceback.format_exc())
                        ams_logger.warning('Exception={}'.str(e))

            else:
                ams_logger.info("No Viya flows were found configured for {}".format(config.run_user))
        else:
            ams_logger.info("Config is not generating Viya flow details")

        for config in ams_config:
            # detect the automations
            ams_logger.info('Detecting automation details from {}'.format(config.config_path))

            if config.AMSProjects:
                for project in config.AMSProjects:
                    for schedule in config.AMSProjects[project].AMSSchedules:
                        configured_automations.append(schedule)

            if config.AMSFileRoutes:
                for schedule in config.AMSFileRoutes:
                    configured_automations.append(schedule)

            if config.AMSFileHandlers:
                for schedule in config.AMSFileHandlers:
                    configured_automations.append(schedule)

            if config.AMSFileParsers:
                for schedule in config.AMSFileParsers:
                    configured_automations.append(schedule)

        out_file.write('<h1>Summary of enabled Automations</h1>')
        out_file.write('<ac:structured-macro ac:name="multiexcerpt-enhanced-permissions"><ac:parameter ac:name="GroupsAllowedToViewAnywhere">{} Jira - Confluence</ac:parameter><ac:parameter ac:name="MultiExcerptName">summary-of-automations</ac:parameter><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:rich-text-body>'.format(tla))
        found_one = False
        for entry in entries:
            if entry['valid'] and not entry['adhoc'] and entry['type'] in TOOLKIT_TYPES:
                automation_name = entry['automation_name']
                if entry['type'] in ('Builtin', 'Data Management', 'Monitoring') or automation_name in configured_automations:
                    ams_logger.info(
                        "Generating {} type={}. It is in crontab AND configured in the json".format(automation_name,
                                                                                                    entry['type']))
                    enabled[automation_name] = entry
                    if not found_one:
                        out_file.write(
                            '<table class="wrapped"><tbody><tr><th>Name</th><th>Type</th><th>Frequency</th><th>Next Scheduled</th></tr>\n')
                        found_one = True
                    if entry['special']:
                        recurrence = '{} &#8211; <b>({})</b>'.format(cleanse_text(entry['description']), cleanse_text(entry['special']).strip())
                    else:
                        recurrence = entry['description']
                    out_file.write(
                        '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(cleanse_text(automation_name),
                                                                                         entry['type'], recurrence,
                                                                                         entry['next_scheduled']))
                else:
                    ams_logger.info("NOT Generating {} type={}. It is in crontab but NOT configured in the json".format(automation_name, entry['type']))
        if found_one:
            out_file.write('</tbody></table>\n\n')
        else:
            out_file.write('<p>None</p>\n\n')
        out_file.write('</ac:rich-text-body></ac:structured-macro>')

        out_file.write('<ac:structured-macro ac:name="multiexcerpt"><ac:parameter ac:name="MultiExcerptName">summary-of-schedules</ac:parameter> <ac:parameter ac:name="hidden">true</ac:parameter><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:rich-text-body>')
        found_one = False
        for entry in entries:
            if entry['valid'] and not entry['adhoc'] and entry['type'] in 'Schedule':
                automation_name = entry['automation_name']
                if automation_name in configured_automations:
                    enabled[automation_name] = entry
                    if not found_one:
                        out_file.write('<table class="wrapped"><tbody><tr><th>Name</th><th>Type</th><th>Frequency</th></tr>\n')
                        found_one = True
                    out_file.write('<tr><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(cleanse_text(automation_name), entry['type'], entry['description']))
        if found_one:
            out_file.write('</tbody></table>\n\n')
        else:
            out_file.write('<p>None</p>\n\n')
        out_file.write('</ac:rich-text-body></ac:structured-macro>')

        out_file.write(
            '<ac:structured-macro ac:name="multiexcerpt"><ac:parameter ac:name="MultiExcerptName">summary-of-file-routes</ac:parameter> <ac:parameter ac:name="hidden">true</ac:parameter><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:rich-text-body>')
        found_one = False
        for entry in entries:
            if entry['valid'] and not entry['adhoc'] and entry['type'] in 'File Route':
                automation_name = entry['automation_name']
                if automation_name in configured_automations:
                    enabled[automation_name] = entry
                    if not found_one:
                        out_file.write(
                            '<table class="wrapped"><tbody><tr><th>Name</th><th>Type</th><th>Frequency</th></tr>\n')
                        found_one = True
                    out_file.write('<tr><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(cleanse_text(automation_name),
                                                                                         entry['type'],
                                                                                         entry['description']))
        if found_one:
            out_file.write('</tbody></table>\n\n')
        else:
            out_file.write('<p>None</p>\n\n')
        out_file.write('</ac:rich-text-body></ac:structured-macro>')

        out_file.write(
            '<ac:structured-macro ac:name="multiexcerpt"><ac:parameter ac:name="MultiExcerptName">summary-of-file-handlers</ac:parameter> <ac:parameter ac:name="hidden">true</ac:parameter><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:rich-text-body>')
        found_one = False
        for entry in entries:
            if entry['valid'] and not entry['adhoc'] and entry['type'] in 'File Handler':
                automation_name = entry['automation_name']
                enabled[automation_name] = entry
                if not found_one:
                    out_file.write(
                        '<table class="wrapped"><tbody><tr><th>Name</th><th>Type</th><th>Frequency</th></tr>\n')
                    found_one = True
                out_file.write(
                    '<tr><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(cleanse_text(automation_name), entry['type'],
                                                                          entry['description']))
        if found_one:
            out_file.write('</tbody></table>\n\n')
        else:
            out_file.write('<p>None</p>\n\n')
        out_file.write('</ac:rich-text-body></ac:structured-macro>')

        out_file.write(
            '<ac:structured-macro ac:name="multiexcerpt"><ac:parameter ac:name="MultiExcerptName">summary-of-file-parsers</ac:parameter> <ac:parameter ac:name="hidden">true</ac:parameter><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:rich-text-body>')
        found_one = False
        for entry in entries:
            if entry['valid'] and not entry['adhoc'] and entry['type'] in 'File Parser':
                automation_name = entry['automation_name']
                if automation_name in configured_automations:
                    enabled[automation_name] = entry
                    if not found_one:
                        out_file.write(
                            '<table class="wrapped"><tbody><tr><th>Name</th><th>Type</th><th>Frequency</th></tr>\n')
                        found_one = True
                    out_file.write('<tr><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(cleanse_text(automation_name),
                                                                                         entry['type'],
                                                                                         entry['description']))
        if found_one:
            out_file.write('</tbody></table>\n\n')
        else:
            out_file.write('<p>None</p>\n\n')
        out_file.write('</ac:rich-text-body></ac:structured-macro>')

        out_file.write('<h1>Adhoc Automations in crontab and atq</h1>')
        out_file.write('<ac:structured-macro ac:name="multiexcerpt"><ac:parameter ac:name="MultiExcerptName">adhoc-automations</ac:parameter><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:rich-text-body>')
        found_one = False
        for entry in entries:
            if entry['valid'] and entry['adhoc']:
                if not found_one:
                    out_file.write(
                        '<table class="wrapped"><tbody><tr><th>Name</th><th>Type</th><th>Frequency</th></tr>\n')
                    found_one = True
                automation_name = entry['automation_name']
                if automation_name == '':
                    automation_name = entry['job']
                out_file.write(
                    '<tr><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(cleanse_text(automation_name), entry['type'],
                                                                          entry['description']))
        if found_one:
            out_file.write('</tbody></table>\n\n')
        else:
            out_file.write('<p>None</p>\n\n')
        out_file.write('</ac:rich-text-body></ac:structured-macro>')

        out_file.write('<h1>Non monitored crontab Automations</h1>')
        found_one = False
        for entry in entries:
            if entry['valid'] and not entry['adhoc'] and entry['type'] not in TOOLKIT_TYPES:
                if not found_one:
                    found_one = True
                    out_file.write(
                        '<ac:structured-macro ac:name="expand"><ac:parameter ac:name="title">Expand to view all automations</ac:parameter><ac:rich-text-body>\n')
                    out_file.write(
                        '<ac:structured-macro ac:name="multiexcerpt"><ac:parameter ac:name="MultiExcerptName">all-automations</ac:parameter><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:rich-text-body>')
                    out_file.write(
                        '<table class="wrapped"><tbody><tr><th>Name</th><th>Type</th><th>Frequency</th></tr>\n')
                out_file.write(
                    '<tr><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(cleanse_text(entry['job']), entry['type'],
                                                                          entry['description']))
        if found_one:
            out_file.write('</tbody></table>\n')
            out_file.write('</ac:rich-text-body></ac:structured-macro>')
            out_file.write('</ac:rich-text-body></ac:structured-macro>\n\n')
        else:
            out_file.write('<p>None</p>\n\n')

        out_file.write('<h1>Configured Automations</h1>\n')
        need_overview = True

        # List all the configured flows for the runuser
        if FileExistsValidator.is_readable(auth_file):
            try:
                out_file.write(generate_viya_flows(auth_file, config))
            except Exception as e:
                ams_logger.warning("Viya Config is invalid e={}".format(e))

        for config in ams_config:
            # generate the automations
            ams_logger.info('Generating automation details from {}'.format(config.config_path))

            project = None
            if args.project:
                project = args.project.strip()

            out_file.write(generate_schedules(config, project, out_file, priority, enabled))
            out_file.write(generate_file_routes(config, out_file, priority, enabled))
            out_file.write(generate_file_parsers(config, out_file, priority, enabled))
            out_file.write(generate_file_handlers(config, out_file, priority, enabled))

        out_file.write('<h1>Unscheduled Automations</h1>\n')
        out_file.write(
            '<ac:structured-macro ac:name="multiexcerpt"><ac:parameter ac:name="MultiExcerptName">unscheduled-automations</ac:parameter><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:rich-text-body>')
        if len(unscheduled):
            out_file.write(unscheduled_automations(unscheduled))
        else:
            out_file.write('<p>None</p>\n\n')
        out_file.write('</ac:rich-text-body></ac:structured-macro>')

        out_file.write('<h1>Configured Secrets</h1>\n')
        out_file.write(
            '<ac:structured-macro ac:name="multiexcerpt"><ac:parameter ac:name="MultiExcerptName">configured-secrets</ac:parameter><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:rich-text-body>')
        out_file.write(generate_secrets(config, out_file))
        out_file.write('</ac:rich-text-body></ac:structured-macro>')
        out_file.write('</ac:rich-text-body></ac:structured-macro>')

        do_confluence = False
        if args.generate_confluence and args.force:
            do_confluence= True
        elif args.generate_confluence:
            do_confluence = True
            # check file modification time on config file vs python source and outputfile
            # update confluence if needed
            dirname = os.path.dirname(output_file)
            src_file = __file__
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                ams_logger.logger.info("Running as a pyinstaller bundle need to check binary modification time of {}".format(sys.executable))
                src_file = sys.executable
            if not dirname:
                dirname = os.getcwd()
            if not FileExistsValidator.is_writeable(output_file):
                ams_logger.info('Outputfile {} doesn\'t exist, so doing Confluence update'.format(output_file))
            elif os.path.getmtime(output_file) < os.path.getmtime(src_file):
                ams_logger.info('Confluence Documenter {} recently modified on {}, so doing Confluence update'.format(src_file, datetime.datetime.fromtimestamp(os.path.getmtime(src_file)).strftime('%Y-%m-%d-%H:%M')))
            elif not hasattr(args, 'config_file') and not hasattr(args, 'crontab'):
                ams_logger.info('No config and crontab specified, so doing Confluence update')
            elif args.config_file is None:
                ams_logger.info('No config specified, so doing Confluence update')
            elif not FileExistsValidator().is_writeable(output_file):
                ams_logger.info('Outputfile {} isn\'t writeable'.format(args.output_file))
            elif not args.config_file and args.crontab_file:
                if os.path.getmtime(output_file) > os.path.getmtime(args.crontab_file):
                    ams_logger.info('Crontab file {} not recently modified, so exiting'.format(args.crontab_file))
                    sys.exit(0)
                else:
                    ams_logger.info('Crontab file {} recently modified, so doing Confluence update'.format(args.crontab_file))
            elif args.config_file and os.path.getmtime(output_file) > os.path.getmtime(args.config_file) and not hash_changed(out_file,output_file):
                ams_logger.info('Config file {} not recently modified compared to dirname={} outputfile {}, so exiting'.format(args.config_file, dirname, output_file))
                sys.exit(0)
            else:
                ams_logger.info('Config file {} recently modified or cron modified, or no config specified, so doing Confluence update'.format(args.config_file))

        # TODO: I'm expecting that when we drop confluence support we'll have separate logic for updating the workstreams.json file
        # TODO: so that's why this is duplicated from above with slightly different behavior
        needs_update = False
        if args.force:
            ams_logger.info('Output was forced to update')
            needs_update = True
        else:
            dirname = os.path.dirname(output_file)
            src_file = __file__
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                ams_logger.logger.info("Running as a pyinstaller bundle need to check binary modification time of {}".format(sys.executable))
                src_file = sys.executable
            if not dirname:
                dirname = os.getcwd()
            if not FileExistsValidator.is_writeable(output_file):
                ams_logger.info('Outputfile {} doesn\'t exist, so doing workstreams.json update'.format(output_file))
                needs_update = True
            elif os.path.getmtime(output_file) < os.path.getmtime(src_file):
                ams_logger.info('Confluence Documenter {} recently modified on {}, so doing workstreams.json update'.format(src_file, datetime.datetime.fromtimestamp(os.path.getmtime(src_file)).strftime('%Y-%m-%d-%H:%M')))
                needs_update = True
            elif not hasattr(args, 'config_file') and not hasattr(args, 'crontab'):
                ams_logger.info('No config and crontab specified, so doing workstreams.json update')
                needs_update = True
            elif args.config_file is None:
                ams_logger.info('No config specified, so doing workstreams.json update')
                needs_update = True
            elif not FileExistsValidator().is_writeable(output_file):
                ams_logger.info('Outputfile {} isn\'t writeable, so NOT doing workstreams.json update'.format(args.output_file))
                needs_update = False
            elif not args.config_file and args.crontab_file:
                if os.path.getmtime(output_file) > os.path.getmtime(args.crontab_file):
                    ams_logger.info('Crontab file {} not recently modified, so NOT doing workstreams.json update'.format(args.crontab_file))
                    needs_update = False
                else:
                    ams_logger.info('Crontab file {} recently modified, so doing workstreams.json update'.format(args.crontab_file))
                    needs_update = True
            elif args.config_file and os.path.getmtime(output_file) > os.path.getmtime(args.config_file) and not hash_changed(out_file, output_file):
                ams_logger.info('Config file {} not recently modified compared to dirname={} outputfile {}, so NOT doing workstreams.json update'.format(args.config_file, dirname, output_file))
                needs_update = False
            else:
                ams_logger.info('Config file {} recently modified or cron modified, or no config specified, so doing workstreams.json update'.format(args.config_file))
                needs_update = True

        if needs_update:
            try:
                # ensure old_workstreams is always defined
                old_workstreams = None
                # check to see if file already exists.
                # if it does, read in the json and set any projects that are not set in the new workstreams
                if FileExistsValidator.is_readable(WORKSTREAMS_FILENAME):
                    try:
                        with open(WORKSTREAMS_FILENAME, 'r') as f:
                            old_workstreams = json.load(f)
                    except Exception as e:
                        old_workstreams = None
                        pass

                # TODO: this needs to change to read the file and only modify the project being documented because a config can have more than one project or --all-projects could be used
                with open(WORKSTREAMS_FILENAME, 'w') as f:
                    if len(config.AMSProjects) > 0:
                        found_project = config.AMSProjects.values()[0]
                        ams_logger.info('Generating {} file based from project name={}'.format(WORKSTREAMS_FILENAME, found_project.project_name))
                    else:
                        ams_logger.warning('No project found, generating {} file based on limited information'.format(WORKSTREAMS_FILENAME))
                        ams_logger.warning('Please add a project to the {} config file'.format(config.config_path))
                        found_project = None

                    workstreams = {'hostname': config.my_hostname, 'timezone': time.tzname[0],
                                   'proxies': {}, 'workstreams': {}, 'last_update': str(datetime.datetime.now()) }
                    if config.zabbix_proxy:
                        workstreams['proxies']['zabbix'] = config.zabbix_proxy
                    if 'http_proxy' in os.environ:
                        workstreams['proxies']['http'] = os.environ['http_proxy']
                    if 'https_proxy' in os.environ:
                        workstreams['proxies']['https'] = os.environ['https_proxy']
                    repository = {}
                    secrets = {}
                    jobs = {}
                    schedule = {}
                    if found_project:
                        project_name = found_project.project_name
                        project_path = found_project.home_dir
                    else:
                        project_name = 'None'
                        project_path = config.config_dir

                    # examine all the workstreams in the previously written file
                    if old_workstreams:
                        try:
                            for old_project_name in old_workstreams['workstreams']:
                                if old_project_name == project_name:
                                    # if it's the same name, then don't copy it over to the new one because it will be updated
                                    pass
                                else:
                                    # if it's not the workstream we're updating here, then copy it over so we can
                                    # support multiple instances of ams_confluence_doc.py running but updating the same file
                                    workstreams['workstreams'][old_project_name] = old_workstreams['workstreams'][old_project_name]
                        except Exception as e:
                            pass

                    workstreams['workstreams'][project_name] = {'path': project_path, 'config_file': config.config_path, 'runuser': config.run_user, 'repository': repository, 'secrets': secrets, 'jobs': jobs, 'schedule': schedule}

                    # detect and add repository info
                    if FileExistsValidator.directory_exists(os.path.join(project_path, ".git")):
                        workstreams['workstreams'][project_name]['repository'] = { "path": project_path, "type": "git"}
                    else:
                        if FileExistsValidator.directory_exists(os.path.join(project_path, ".svn")):
                            workstreams['workstreams'][project_name]['repository'] = {"path": project_path, "type": "svn"}

                    # add ids for configured secrets
                    for secret in six.itervalues(config.AMSSecrets):
                        docs = generate_one_secret(config, secret, False)
                        secrets[secret.secret_name] = {'name': secret.secret_name, 'id': secret.secret_id, 'url': 'https://securevault.sas.com/secretserver/app/#/secret/{}/general'.format(secret.secret_id), 'html': docs}


                    # add list of configured schedules to jobs
                    if found_project and found_project.AMSSchedules and len(found_project.AMSSchedules):
                        for job in six.itervalues(found_project.AMSSchedules):
                            docs = generate_one_schedule(job, False)
                            jobs[job.schedule_name] = {'name': job.schedule_name, 'type': 'Schedule', 'html': docs}

                    # add list of configured file routes to jobs
                    if config.AMSFileRoutes and len(config.AMSFileRoutes):
                        for job in six.itervalues(config.AMSFileRoutes):
                            docs = generate_one_file_route(job, False)
                            jobs[job.file_route_name] = {'name': job.file_route_name, 'type': 'File Route', 'html': docs}

                    # add list of configured file handlers to jobs
                    if config.AMSFileHandlers and len(config.AMSFileHandlers):
                        for job in six.itervalues(config.AMSFileHandlers):
                            docs = generate_one_file_handler(job, False)
                            jobs[job.file_handler_name] = {'name': job.file_handler_name, 'type': 'File Handler', 'html': docs}

                    # add list of configured file parsers to jobs
                    if config.AMSFileParsers and len(config.AMSFileParsers):
                        for job in six.itervalues(config.AMSFileParsers):
                            docs = generate_one_file_parser(job, False)
                            jobs[job.file_parser_name] = {'name': job.file_parser_name, 'type': 'File Parser', 'html': docs}

                    # add list of crontab / at jobs
                    for entry in entries:
                        # hack the next_scheduled to be a string
                        if entry['type'] != 'other' and (not str(entry['type']).startswith('sso_')):
                            if entry['automation_name'] in schedule:
                                slist = schedule[entry['automation_name']]
                            else:
                                slist = []
                                schedule[entry['automation_name']] = slist
                        elif entry['type']:
                            if entry['type'] in schedule:
                                slist = schedule[entry['type']]
                            else:
                                slist = []
                                schedule[entry['type']] = slist
                        else:
                            if 'adhoc' in schedule:
                                slist = schedule['adhoc']
                            else:
                                slist = []
                                schedule['adhoc'] = slist

                        entry['next_scheduled'] = str(entry['next_scheduled'])
                        slist.append(entry)

                    # this sucks. we need to null out the "html" docs because the json doc is too big for zabbix
                    if len(json.dumps(workstreams, indent=0)) > 32000:
                        ams_logger.warning('Generated workstreams.json is too large with HTML documentation. Removing HTML docs unfortunately')
                        try:
                            for workstream in workstreams['workstreams']:
                                for job in workstreams['workstreams'][workstream]['jobs']:
                                    if 'html' in workstreams['workstreams'][workstream]['jobs'][job]:
                                        del workstreams['workstreams'][workstream]['jobs'][job]['html']
                                for secret in workstreams['workstreams'][workstream]['secrets']:
                                    if 'html' in workstreams['workstreams'][workstream]['secrets'][secret]:
                                        del workstreams['workstreams'][workstream]['secrets'][secret]['html']
                        except:
                            pass

                    json.dump(workstreams, f, indent=0)
            except Exception as e:
                ams_logger.error('Apologies but the workspace.json generation had an exception={}'.format(str(e)))

        # always write the new file
        with open(output_file, 'w') as f:
            f.write(out_file.getvalue())
        # optionally update confluence
        if do_confluence:
            # Secret must be pre-configured, use the ams_config of the first config
            config = ams_config[0]
            secret_server = AMSSecretServer(username=config.decrypt(ams_defaults.thycotic_func_username), password=config.decrypt(ams_defaults.thycotic_func_password), domain="")
            token = secret_server.get_amspassword_secret(ams_defaults.default_confluence_secret_id).password

            content = out_file.getvalue()
            content = content.replace('\n', '')
            content = content.replace('"', '\\"')

            # grab space_name and confluence_title from config
            space_name = config.get_my_environment().confluence_space

            if not space_name:
                space_name = 'SSODMAS'
                ams_logger.warning('No confluence_space configured in environment section of config.')

            project_name = None
            try:
                x = config.AMSProjects.values()
                project_name = config.AMSProjects.values()[0].project_name
            except:
                pass

            if args.confluence_title:
                confluence_title = args.confluence_title.strip()
            else:
                confluence_title = 'Automation Details'
                if project_name:
                    confluence_title += ' - ' + project_name

            ams_logger.info('Outputting HTML Confluence page in space_name {} searching for page_title {}'.format(space_name, confluence_title))
            update_page(token, space_name, confluence_title, content)

    except AMSConfigException as e:
        print('AMSConfigException encountered: %s' % str(e))
    except Exception as e:

        print('Exception encountered: %s' % str(e))