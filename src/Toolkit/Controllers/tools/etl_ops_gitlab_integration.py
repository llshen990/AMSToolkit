import sys
import os
import traceback
import json
import requests
import cgi
import logging
from datetime import datetime, timedelta
import dateutil.parser as parser
from jira import JIRA, JIRAError
import base64

from Toolkit.Lib.Helpers.AMSJiraIssue import AMSJiraIssue

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger


def get_token(token_file_path):
    try:
        with open(token_file_path, 'r') as f:
            return f.readline().strip()
    except Exception as e:
        raise Exception('Problem reading credentials file, {}', token_file_path)


def get_json(token, lastDate):
    try:
        formattedDate = parser.parse(lastDate).isoformat()[:-3] + 'Z'
        url = 'https://gitlab.sas.com/api/v4/groups/ssoappmgmt/merge_requests/?scope=all&target_branch=staging&state=opened&created_after={}'.format(
            formattedDate)
        logging.getLogger('AMS').info("Gitlab query url={}".format(url))
        response = requests.get(cgi.escape(url), headers={'PRIVATE-TOKEN': token})
        if not response.status_code == 200:
            raise Exception('Problem with query response={}'.format(response.text))
        try:
            value = json.loads(response.text)
        except Exception as e:
            value = []
        return value
    except Exception as e:
        logging.getLogger('AMS').error("Caught an exception running {}: {}".format(__file__, e))
        logging.getLogger('AMS').error("Traceback: " + traceback.format_exc())
        return None


def map_username_to_assginee(username):
    try:
        if username[0].isupper():
            try:
                tokens = username.lower().split('.')
                return tokens[0][0:2] + tokens[1][0:4]
            except Exception as e:
                logging.getLogger('AMS').error("Caught an exception running {}: {}".format(__file__, e))
                logging.getLogger('AMS').error("Traceback: " + traceback.format_exc())
        else:
            return username
    except Exception as e:
        # not the best way to handle this
        pass

    return None


if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    ams_logger.set_debug(True)

    # save 'now' so we can write it out later as gitlab.txt
    # Note: gitlab times are in ISO format and Zulu time is preferred
    startDate = datetime.utcnow().isoformat() + 'Z'

    root_dir = os.path.dirname(os.path.abspath(__file__))
    ams_logger.info('Using root_dir={}'.format(root_dir))

    gitlab_token = get_token(os.path.join(root_dir, 'gitlab.credentials'))

    try:
        with open(os.path.join(root_dir, 'gitlab.txt'), 'r') as f:
            lastDate = f.readline().strip()
        ams_logger.info('Read gitlab.txt time as datetime={}'.format(lastDate))
    except Exception as e:
        # default to now
        lastDate = startDate

    merge_requests = get_json(gitlab_token, lastDate)
    if merge_requests is None:
        raise Exception('Problem authenticating. Check username and password.')

    ams_logger.info('Authenticated successfully')

    ams_logger.info('Found {} open merge requests'.format(len(merge_requests)))

    # instantiate a jira client
    JIRA_HOST = "https://www.ondemand.sas.com/jira/"
    user, password = base64.b64decode(get_token(os.path.join(root_dir, 'credentials'))).strip().split(':')
    jira = JIRA({"server": JIRA_HOST}, basic_auth=(user, password))

    for merge_request in merge_requests:
        ams_logger.info('New merge request iid={} author={} title={}, web_url={}'.format(merge_request['iid'],
                                                                                         merge_request['author'],
                                                                                         merge_request['title'],
                                                                                         merge_request['web_url']))
        username = merge_request['author']['username']
        assignee = map_username_to_assginee(username)

        # Do some cheesy string munging of the title to let it appear a bit more presentable
        summary = str(merge_request['title'])
        try:
            if str.startswith(summary, 'Draft: '):
                summary = summary[7:]
            if str.startswith(summary, 'Resolve "'):
                summary = summary[9:-1]
        except Exception:
            pass

        # create an issue for each merge request
        issue = AMSJiraIssue()
        issue.add_summary(summary='AMP Work: ' + summary)
        if assignee:
            issue.add_description(
                description=summary + os.linesep + os.linesep + 'See the merge request in Gitlab for more information:' + os.linesep +
                            merge_request['web_url'])
        else:
            issue.add_description(
                description=os.linesep + os.linesep + 'NOTE: No username mapping from Gitlab to JIRA exists for assignee {}.'.format(
                    username))

        two_weeks_from_now = datetime.utcnow() + timedelta(days=14)
        issue.add_due_date(two_weeks_from_now.isoformat())

        issue.add_assignee_by_name(assignee=assignee)

        issue.assign_labels(['ETL_OPS_AMP_GITLAB_INTEGRATION'])

        try:
            response = jira.create_issue(issue.fields())
            ams_logger.info('New Jira ticket (key: {}) created'.format(response.key))
            ams_logger.info('Request Payload was {}'.format(issue.fields()))
        except JIRAError as e:
            logging.getLogger('AMS').error("Issue fields: {}".format(issue.fields()))
            logging.getLogger('AMS').error("Caught an exception creating a jira ticket: {}".format(e))
            raise

    try:
        with open(os.path.join(root_dir, 'gitlab.txt'), 'w') as f:
            f.write(startDate)
        ams_logger.info('Wrote gitlab.txt time as datetime={} to directory={}'.format(lastDate, root_dir))
    except Exception as e:
        logging.getLogger('AMS').error("Caught an exception running {}: {}".format(__file__, e))
        logging.getLogger('AMS').error("Traceback: " + traceback.format_exc())
