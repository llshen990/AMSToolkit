import sys
import os
import traceback
import json
import requests
from requests.auth import HTTPBasicAuth
import logging
from datetime import datetime, timedelta
import cgi
import pytz

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Lib.Helpers import SASEmail
from Toolkit.Config import AMSConfig
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Thycotic import AMSSecretServer

def get_json(jql):
    try:
        url = 'https://www.ondemand.sas.com/jira/rest/api/2/search?jql='+jql
        response = requests.get(url, headers = { 'Authorization' : 'Basic {}'.format(token)})
        if not response.status_code == 200:
            raise Exception('Problem with JIRA query response={}'.format(response.text))
        try:
            value = json.loads(response.text)
        except Exception as e:
            value = []
        return value
    except Exception as e:
        logging.getLogger('AMS').error("Caught an exception running {}: {}".format(__file__, e))
        logging.getLogger('AMS').error("Traceback: " + traceback.format_exc())
        return None


def get_issues(jql):
    try:
        try:
            value = get_json(jql)['issues']
        except Exception as e:
            value = []
        return value
    except Exception as e:
        logging.getLogger('AMS').error("Caught an exception running {}: {}".format(__file__, e))
        logging.getLogger('AMS').error("Traceback: " + traceback.format_exc())

def get_total_issues(jql):
    try:
        if jql.startswith('filter='):
            ref = "https://www.ondemand.sas.com/jira/issues/?{}".format(cgi.escape(jql))
        else:
            ref = "https://www.ondemand.sas.com/jira/issues/?jql={}".format(cgi.escape(jql))
        try:
            value = get_json(jql)['total']
        except Exception as e:
            value = '0'
        return "<a href='{}'>{}</a>".format(ref, value)
    except Exception as e:
        logging.getLogger('AMS').error("Caught an exception running {}: {}".format(__file__, e))
        logging.getLogger('AMS').error("Traceback: " + traceback.format_exc())

email_output = ''

def append_email(output):
    global email_output
    email_output += output + os.linesep

if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    ams_logger.set_debug(True)

    # save 'now' so we can write it out later as lastrun.txt
    tz = pytz.timezone('America/New_York')
    now = datetime.now(tz)
    startDate = now.strftime('%Y/%m/%d %H:%M')

    root_dir = os.path.dirname(os.path.abspath(__file__ ))
    ams_logger.info('Using root_dir={}'.format(root_dir))

    token = None

    try:
        try:
            ams_config = AMSConfig()
            ams_defaults = AMSDefaults()
            secret_server = AMSSecretServer(username=ams_config.decrypt(ams_defaults.thycotic_func_username), password=ams_config.decrypt(ams_defaults.thycotic_func_password), domain="")
            token = secret_server.get_amspassword_secret(ams_defaults.default_confluence_secret_id).password
        except Exception as e:
            raise Exception('Problem reading credentials file.')

        try:
            with open(os.path.join(root_dir,'lastrun.txt'), 'r') as f:
                lastDate = f.readline().strip()
            ams_logger.info('Read lastrun.txt time as datetime={}'.format(lastDate))
            # ensure it parses as a datetime?
        except Exception as e:
            # default to 12 hours ago
            twelve_ago = now - timedelta(hours=12)
            lastDate = twelve_ago.strftime('%Y/%m/%d %H:%M')

        # do this initial check so that if it fails, we don't lock out the account
        check = get_json('')
        if not check:
            raise Exception('Problem authenticating to JIRA. Check username and password.')
        ams_logger.info('Authenticated successfully.')

        ams_logger.info('Getting overall ticket status')
        append_email("<h1>ETL Ops Ticket Status as of {}</h1>".format(datetime.strftime(now, "%Y/%m/%d at %H:%M")))
        append_email("<h2><a href='https://www.ondemand.sas.com/jira/secure/Dashboard.jspa?selectPageId=20448'>ETL Ops Incident Dashboard</a></h2>")
        append_email('<table border="1" class="dataframe"><thead><tr><th>Status</th><th>Total</th></tr></thead>')
        append_email("<tbody>")
        append_email('<tr><td>Open Blockers</td><td>{}</td></tr>'.format(get_total_issues('filter=36219')))
        append_email('<tr><td>Issues Queue Unassigned </td><td>{}</td></tr>'.format(get_total_issues('filter=36216')))
        append_email('<tr><td>Issues open <4 days </td><td>{}</td></tr>'.format(get_total_issues('filter=36217')))
        append_email('<tr><td>Issues open >=4 days </td><td>{}</td></tr>'.format(get_total_issues('filter=36177')))
        append_email('<tr><td>Issues in Resolved</td><td>{}</td></tr>'.format(get_total_issues('filter=37478')))
        append_email('<tr><td>Closed over past 14 days</td><td>{}</td></tr>'.format(get_total_issues('(assignee was in membersOf("AMS Member") OR assignee was in membersOf("AMS CRD Member") OR assignee was in membersOf("AMS Pune Member") OR assignee was in (ssoretailops, amsteamjira)) AND type = Issue AND createddate > startOfDay(-14) and status in (Closed) ORDER BY priority DESC, created ASC')))
        append_email("</tbody></table>")
        append_email("<p>Incident tickets are worked with on call resources and include all Issues assigned to the ssoretailops queue.</p><p>Please see <a href='https://www.ondemand.sas.com/confluencedoc/x/vw_l'>Confluence for more information about OnCall teams</a>.</p>")

        ams_logger.info('Getting workflow status')
        append_email("<p><hr/><p>")
        append_email("<h2><a href='https://www.ondemand.sas.com/jira/secure/Dashboard.jspa?selectPageId=20304'>ETL Ops Services Ticket Triage</a></h2>")

        append_email('<table border="1" class="dataframe"><thead><tr style="text-align: left;"><th>Status</th><th>Scheduled Work</th><th>Tasks</th><th>Total</th></tr></thead>')
        append_email("<tbody>")
        ams_logger.info('Getting workflow details - Unassigned')
        scheduled = 'type = "ETL Ops SAS Service Request" AND "Type of Request" in ("Scheduled Work") AND (assignee = etloperationssvcs) AND status in (Open, "On Hold")'
        tasks = 'type = "ETL Ops SAS Service Request" AND "Type of Request" not in ("Scheduled Work") AND (assignee = etloperationssvcs) AND status in (Open, "On Hold")'
        all = 'type = "ETL Ops SAS Service Request" AND (assignee = etloperationssvcs) AND status in (Open, "On Hold")'
        append_email('<tr style="text-align: left;"><th>Unassigned</th><td>{}</td><td>{}</td><td>{}</td></tr>'.format(get_total_issues(scheduled), get_total_issues(tasks), get_total_issues(all)))
        ams_logger.info('Getting workflow details - Open')
        scheduled = 'type = "ETL Ops SAS Service Request" AND "Type of Request" IN ("Scheduled Work") AND (assignee = etloperationssvcs ) AND status in ("Waiting for Input")'
        tasks = 'type = "ETL Ops SAS Service Request" AND ("Type of Request" not IN ("Scheduled Work") OR "TYPE of Request" in (Other, Task, Empty)) AND (assignee = etloperationssvcs ) AND status in ("Waiting for Input")  '
        all = 'type = "ETL Ops SAS Service Request" AND (assignee = etloperationssvcs ) AND status in ("Waiting for Input") '
        append_email('<tr style="text-align: left;"><th>Waiting on ETL Ops</th><td>{}</td><td>{}</td><td>{}</td></tr>'.format(get_total_issues(scheduled), get_total_issues(tasks), get_total_issues(all)))
        ams_logger.info('Getting workflow details - Waiting on Others')
        scheduled = 'type = "ETL Ops SAS Service Request" AND ("Type of Request" IN ("Scheduled Work") ) AND (assignee not in membersOf("AMS Member")) AND status in ("Waiting for Input")'
        tasks = 'type = "ETL Ops SAS Service Request" AND ("Type of Request" not IN ("Scheduled Work") OR "TYPE of Request" in (Other, Task) or "TYPE of Request"  is EMPTY) AND (assignee not in membersOf("AMS Member")) AND status in ("Waiting for Input")'
        all = 'type = "ETL Ops SAS Service Request" AND (assignee not in membersOf("AMS Member")) AND status in ("Waiting for Input")'
        append_email('<tr style="text-align: left;"><th>Waiting on Others</th><td>{}</td><td>{}</td><td>{}</td></tr>'.format(get_total_issues(scheduled), get_total_issues(tasks), get_total_issues(all)))
        ams_logger.info('Getting workflow details - Scheduled')
        scheduled = 'type = "ETL Ops SAS Service Request" AND "Type of Request" IN ("Scheduled Work")  AND status in ("Scheduled")'
        tasks = 'type = "ETL Ops SAS Service Request" AND ("Type of Request" not IN ("Scheduled Work") OR "TYPE of Request" in (Other, Task, Empty)) AND status in ("Scheduled")'
        all = 'type = "ETL Ops SAS Service Request" AND status in ("Scheduled")'
        append_email('<tr style="text-align: left;"><th>Scheduled</th><td>{}</td><td>{}</td><td>{}</td></tr>'.format(get_total_issues(scheduled), get_total_issues(tasks), get_total_issues(all)))
        ams_logger.info('Getting workflow details - In Progress')
        scheduled = 'type = "ETL Ops SAS Service Request" AND ("Type of Request" IN ("Scheduled Work")) AND status in ("Work In Progress")'
        tasks = 'type = "ETL Ops SAS Service Request" AND ("Type of Request" NOT IN ("Scheduled Work")) AND status in ("Work In Progress")'
        all = 'type = "ETL Ops SAS Service Request" AND status in ("Work In Progress")'
        append_email('<tr style="text-align: left;"><th>In Progress</th><td>{}</td><td>{}</td><td>{}</td></tr>'.format(get_total_issues(scheduled), get_total_issues(tasks), get_total_issues(all)))
        ams_logger.info('Getting workflow details - On Hold')
        scheduled = 'type = "ETL Ops SAS Service Request" AND ("Type of Request" IN ("Scheduled Work")) AND status in ("On Hold")'
        tasks = 'type = "ETL Ops SAS Service Request" AND ("Type of Request" NOT IN ("Scheduled Work")) AND status in ("On Hold")'
        all = 'type = "ETL Ops SAS Service Request" AND status in ("On Hold")'
        append_email('<tr style="text-align: left;"><th>On Hold</th><td>{}</td><td>{}</td><td>{}</td></tr>'.format(get_total_issues(scheduled), get_total_issues(tasks), get_total_issues(all)))
        append_email('<tr style="text-align: left;"><th>Stale Tickets</th><td></td><td></td><td>{}</td></tr>'.format(get_total_issues('filter=35846')))
        append_email('<tr style="text-align: left;"><th>Untriaged Service Requests</th><td></td><td></td><td>{}</td></tr>'.format(get_total_issues('filter=35834')))
        append_email('<tr style="text-align: left;"><th>Expedited Tickets</th><td></td><td></td><td>{}</td></tr>'.format(get_total_issues('filter=35838')))
        append_email("</tbody></table>")

        append_email("<p>ETL Ops SAS Service requests are worked during Cary business hours.</p><p>Please see <a href='https://www.ondemand.sas.com/confluencedoc/x/Z1wYAw'>Confluence for more information about ticket triage</a>.</p>")
        append_email("")
        append_email("<br>")
        append_email("<p><hr/><p>")

        ams_logger.info('Getting ticket status as of {}'.format(lastDate))
        incidents = 'filter=37241 AND type in (Issue) AND (createdDate < "{}") AND (createdDate > "{}") order by Status ASC, Priority DESC'.format(startDate, lastDate)
        issues = get_issues(incidents)
        ams_logger.info('Found {} incidents'.format(len(issues)))
        append_email("<h2>{} Incident tickets <a href='https://www.ondemand.sas.com/jira/issues/?jql={}'>created between {} and {}</a></h2>".format(len(issues), cgi.escape(incidents), lastDate, startDate))
        if len(issues) > 0:
            append_email("")
            append_email('<table border="1" class="dataframe"><thead><tr><th>Key</th><th>Priority</th><th>Date</th><th>Summary</th><th>Resolution</th></tr></thead>')
            append_email("<tbody>")
            for issue in issues:
                be_bold = False
                if issue['fields']['priority']['name'] == 'Blocker':
                    be_bold = True
                if issue['fields']['resolution']:
                    status = '{} / {}'.format(issue['fields']['status']['name'], issue['fields']['resolution']['name'])
                    be_bold = False
                else:
                    status = issue['fields']['status']['name']
                url = 'https://www.ondemand.sas.com/jira/browse/{}'.format(issue['key'])
                summary = cgi.escape(issue['fields']['summary'])
                # This is user entered text so ensure it is ascii
                summary = summary.encode('ascii', 'ignore')
                if be_bold:
                    append_email('<td><b><a href={}>{}</a></td><td><b>{}</td><td>{}</td><td><b>{}</td><td><b>{}</td></tr>'.format(url, issue['key'], issue['fields']['priority']['name'], issue['fields']['created'], summary, status))
                else:
                    append_email('<td><a href={}>{}</a></td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(url, issue['key'], issue['fields']['priority']['name'], issue['fields']['created'], summary, status))
            append_email("</tbody></table>")

        ams_logger.info('Sending email')
        email = SASEmail()
        email.set_to('robert.ward@sas.com, ken.persson@sas.com, dave.setzer@sas.com')
        email.set_html_message(email_output)
        email.set_subject('ETL OPS shift wrap up report')
        email.send()

        exit_code = 0

    except Exception as e:
        # noinspection PyUnboundLocalVariable
        ams_logger.error("Caught an exception running %s: %s" % (__file__, str(e)))
        ams_logger.error("Traceback: " + traceback.format_exc())

        description = "Error message: %s" % str(e)
        description += "\n\nStack Trace:\n"
        description += traceback.format_exc()

        zabbix = AMSZabbix(ams_logger)
        jibbix = AMSDefaults().AMSJibbixOptions
        jibbix.labels = 'ams_toolkit, ETL_OPS_AUTOMATION'
        jibbix.summary = 'Automation Failed: ETL Ops Ticket Summmary'
        zabbix.call_zabbix_sender(AMSDefaults().default_zabbix_key_no_schedule, jibbix.str_from_options() + "\n" + description)

        exit_code = 1

    if exit_code == 0:
        try:
            lastRun = now.strftime('%Y/%m/%d %H:%M')
            with open(os.path.join(root_dir, 'lastrun.txt'), 'w') as f:
                f.write(startDate)
            ams_logger.info('Wrote lastrun.txt time as datetime={} to directory={}'.format(startDate, root_dir))
        except Exception as e:
            logging.getLogger('AMS').error("Caught an exception running {}: {}".format(__file__, e))
            logging.getLogger('AMS').error("Traceback: " + traceback.format_exc())

    sys.exit(exit_code)

