import argparse
import sys
import time
import datetime
import traceback
import readline
import getpass
import smtplib
import urllib
from jira import JIRA
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Models import AMSScheduleLLD, AMSFileRouteLLD
from Toolkit.Exceptions import AMSExceptionNoEventNotification, AMSConfigException, AMSLldException, AMSZabbixException
from Toolkit.Config import AMSConfig
from Toolkit.Lib.Defaults import AMSDefaults

CONTENTS = []
mute = None

def _get_credentials():
    readline.set_startup_hook(lambda: readline.insert_text(current_user))
    user = raw_input('Enter Your Zabbix Username (VSP): ')
    readline.set_startup_hook()
    passwd = getpass.getpass('Enter Your Zabbix Password (VSP): ')
    return user, passwd

def _print_or_store(stdout):
    if mute is None:
        print(stdout)
    else:
        CONTENTS.append(stdout)

def _send_mail(user_email):
    msg = MIMEMultipart()
    msg['From'] = '{}@vsp.sas.com'.format(current_user)
    msg['To'] = user_email
    msg['Subject'] = 'Results from {} on {} at {}'.format(__file__, AMSDefaults().my_hostname, datetime.datetime.now().isoformat())
    msg.attach(MIMEText('\n'.join(CONTENTS)))
    with open(ams_logger.app_log_filename(), 'r') as log:
        msg.attach(MIMEApplication(log.read(), Name=ams_logger.app_log_filename()))
    smtp = smtplib.SMTP('localhost')
    smtp.sendmail(msg['From'], msg['To'], msg.as_string())
    smtp.close()


def check_authentication():
    if not ams_schedule_lld.is_authenticated():
        _print_or_store('Zabbix REST call failed trying to check template. Unsetting environment proxies and retrying')
        os.environ['http_proxy'] = ''
        os.environ['https_proxy'] = ''
        os.environ['HTTP_PROXY'] = ''
        os.environ['HTTPS_PROXY'] = ''
        return ams_schedule_lld.is_authenticated()
    return True


def apply_template_to_host(template_name):
    _print_or_store('Determining if %s template is applied to host %s' % (template_name, ams_config.my_hostname))
    already_applied = ams_schedule_lld.is_template_applied_to_host(template_name, ams_config.my_hostname)
    if already_applied:
        _print_or_store('%s template is already applied!' % template_name)
    else:
        _print_or_store('%s template is not applied, working on applying it now...' % template_name)
        if ams_schedule_lld.apply_template_to_host(template_name, ams_config.my_hostname):
            _print_or_store('%s template has successfully been applied to host %s' % (template_name, ams_config.my_hostname))
            try:
                max_iterations = 10
                for iteration in range(1, max_iterations+1):
                    template_applied = ams_schedule_lld.is_template_applied_to_host(template_name, ams_config.my_hostname)
                    if not template_applied:
                        _print_or_store('%s template is NOT yet present on host %s' % (template_name, ams_config.my_hostname))
                        _print_or_store('Sleeping for 1 minute...')
                        time.sleep(minute)
                    else:
                        _print_or_store('%s template has been confirmed to be added to host %s' % (template_name, ams_config.my_hostname))
                        break
            except Exception as e:
                raise AMSLldException('Unable to determine template status')
        else:
            raise AMSLldException('Could not apply the template to host for an unknown reason!')
    return already_applied


if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    current_user = AMSDefaults().current_user
    ams_defaults = AMSDefaults()

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--config_file", nargs='?', type=str, help="Config File", required=True)
    # noinspection PyTypeChecker
    arg_parser.add_argument("--apply_templates", action='store_true', help="Apply Zabbix Templates if needed", default=False, required=False)
    # run in the background and email results instead
    # noinspection PyTypeChecker
    arg_parser.add_argument("-e", "--email", required=False, type=str, help="Email address to send results to.")
    arg_parser.add_argument("-u", "--username", required=False, type=str, default='', help="Zabbix username for automated runs")
    arg_parser.add_argument("-p", "--password", required=False, type=str, default='', help="Zabbix password for automated runs")

    args = arg_parser.parse_args()
    ams_logger.debug('config_file=%s' % str(args.config_file).strip())
    apply_templates = args.apply_templates
    email = args.email if args.email is not '' else None

    ams_config = AMSConfig(str(args.config_file).strip())
    ams_logger.set_debug(ams_config.debug)

    if ams_config.new_config:
        raise AMSExceptionNoEventNotification('Config file of %s does not currently exist.  You must specify a valid config.' % args.config_file)

    # if we don't pass in the host, we'll grab it from the config and it will be assumed to be the current host.
    ams_logger.debug('host=%s' % ams_config.my_hostname)

    minute = 0 if ams_defaults.is_dev_host() else 60

    if apply_templates:
        try:
            username, password = _get_credentials()
        except Exception as e:
            raise AMSLldException('Failed to capture user credentials.')
    else:
        username = current_user
        password = None

    # daemonize
    if email is not None:
        p = os.fork()
        if p > 0:
            print('Daemonizing... Upon completion you will receive an email at {}'.format(email))
            print('If you do not receive the email within 24 hours check the logs.')
            sys.exit(0)
        os.setsid()
        f = open(os.devnull, 'w')
        sys.stdout = sys.stderr = f
        mute = True
    time.sleep(1)  # Takes a moment for original proc to die

    try:
        my_environment = ams_config.get_my_environment()
    except AMSConfigException as e:
        ams_logger.error('Current hostname=%s does not exist in environment config.  Please define in environment config or check to make sure you are running on correct host: %s.' % (ams_config.my_hostname, str(e)))
        raise

    file_route_lld = AMSFileRouteLLD(ams_config, ams_defaults.zabbix_file_route_lld_key, username=username, password=password)
    ams_schedule_lld = AMSScheduleLLD(ams_config, ams_defaults.zabbix_batch_monitoring_lld_key, username=username, password=password)

    try:
        if apply_templates:
            if not check_authentication():
                raise AMSZabbixException('Credentials are not valid or there is a problem connecting to Zabbix REST API over HTTPs')

            # Add Schedule template
            if apply_template_to_host(ams_defaults.zabbix_template_name):
                apply_templates = False
                ams_logger.info("Templates are already applied, so not doing any more REST calls")
            else:
                # Add WebScenario template
                apply_template_to_host(ams_defaults.zabbix_web_template_name)

        # Make LLD dictionary
        _print_or_store('Zabbix is configured enough to make our LLD call, generating Schedule LLD dictionary based off the AMS Config file...')
        ams_schedule_lld.generate_lld_dict()

        _print_or_store('Schedule LLD dictionary created, invoking Zabbix LLD call...We will try up to %s times to make the LLD call.' % ams_defaults.zabbix_setup_iterations_to_wait)
        _print_or_store('If this fails and times out, you need to investigate the root cause.')

        for i in range(ams_defaults.zabbix_setup_iterations_to_wait):
            if not ams_defaults.is_dev_host():
                _print_or_store('Sleeping %s seconds.  Iteration #%s of %s' % (ams_defaults.zabbix_setup_iteration_duration, i + 1, ams_defaults.zabbix_setup_iterations_to_wait))
                time.sleep(ams_defaults.zabbix_setup_iteration_duration)
            _print_or_store('Invoking Schedule LLD call...')
            try:
                if ams_schedule_lld.invoke_zabbix_lld():
                    break
                else:
                    if apply_templates:
                        ams_schedule_lld.clear_proxy_config_cache()
            except AMSZabbixException as e:
                _print_or_store('Schedule LLD call failed...')
        else:
            raise AMSLldException('Zabbix failed to process our Schedule LLD config properly.  Please investigate.')

        _print_or_store('Successfully configured our host %s with our Schedule LLD configuration in Zabbix.' % ams_config.my_hostname)

        file_route_lld.generate_lld_dict()

        # Make LLD dictionary
        _print_or_store('Zabbix is configured enough to make our LLD call, generating FileRoute LLD dictionary based off the AMS Config file...')
        file_route_lld.generate_lld_dict()

        _print_or_store('FileRoute LLD dictionary created, invoking Zabbix LLD call...We will try up to %s times to make the LLD call.' % ams_defaults.zabbix_setup_iterations_to_wait)
        _print_or_store('If this fails and times out, you need to investigate the root cause.')

        for i in range(ams_defaults.zabbix_setup_iterations_to_wait):
            if not ams_defaults.is_dev_host():
                _print_or_store('Sleeping %s seconds.  Iteration #%s of %s' % (ams_defaults.zabbix_setup_iteration_duration, i + 1, ams_defaults.zabbix_setup_iterations_to_wait))
                time.sleep(ams_defaults.zabbix_setup_iteration_duration)
            _print_or_store('Invoking FileRoute LLD call...')
            try:
                if file_route_lld.invoke_zabbix_lld():
                    break
                else:
                    if apply_templates:
                        file_route_lld.clear_proxy_config_cache()
            except AMSZabbixException as e:
                _print_or_store('FileRoute LLD call failed...')
        else:
            raise AMSLldException('Zabbix failed to process our FileRoute LLD config properly.  Please investigate.')

        _print_or_store('Successfully configured our host %s with our FileRoute LLD configuration in Zabbix.' % ams_config.my_hostname)

        if apply_templates:
            _print_or_store('Checking to see if host %s is in host group: %s' % (ams_config.my_hostname, ams_defaults.zabbix_hostgroup_name))

            _print_or_store('Sleeping for 3 minutes...')
            time.sleep(3 * minute)

        if apply_templates:
            if ams_schedule_lld.is_host_in_host_group(ams_config.my_hostname, ams_defaults.zabbix_hostgroup_name):
                _print_or_store('%s is already in host group %s' % (ams_config.my_hostname, ams_defaults.zabbix_hostgroup_name))
            else:
                _print_or_store('%s host group is not configured for host %s, adding it now...' % (ams_defaults.zabbix_hostgroup_name, ams_config.my_hostname))
                if not ams_schedule_lld.add_host_to_host_group(ams_config.my_hostname, ams_defaults.zabbix_hostgroup_name):
                    raise AMSLldException('Could not add host to host group for an unknown reason!')

        _print_or_store('Everything should now be setup for host: %s' % ams_config.my_hostname)
        _print_or_store('Sending in a test JIBBIX alert...')
        retry = ams_defaults.test_jira_retries
        query = 'project = "SSO"  and assignee = {} and priority = Critical ORDER BY createdDate DESC'.format(username)
        auth_jira = None
        if not ams_defaults.is_dev_host():
            try:
                auth_jira = JIRA(ams_defaults.jira_base, auth=(username, password))
            except:  # This error message may contain password so do not capture.
                _print_or_store('Unable to connect to JIRA, attempting to create test ticket anyway.')
        while retry > 0:
            if ams_schedule_lld.test_zabbix_ticket_generation(ams_config.my_hostname, username=username):
                if auth_jira:
                    issues = auth_jira.search_issues(query)
                    if len(issues) > 0:
                        _print_or_store('Please check JIRA and close (not resolve) the test issue as testing.')
                        _print_or_store(issues[0].permalink())
                    else:
                        _print_or_store('Jira reported no matching issues. Attempting to create test ticket again.')
                        retry -= 1
                        continue
                else:
                    _print_or_store('Zabbix ticket generation was reported successful. Please check JIRA and close (not resolve) the issue as testing.')
                    url = '{}issues/?jql={}'.format(ams_defaults.jira_base, urllib.quote(query))
                    _print_or_store('It should be the first entry if you navigate to this URL:')
                    _print_or_store(url)
                retry = 0
            else:
                retry -= 1
                _print_or_store('Failed to create test ticket. {} retries remain'.format(retry))

    except KeyboardInterrupt:
        _print_or_store('%sUser killed process with ctrl+c...' % os.linesep)
    except AMSExceptionNoEventNotification as e:
        _print_or_store("{}Process exited with a AMSExceptionNoEventNotification exception: {}{}".format(os.linesep, ams_schedule_lld.AMSZabbix.sanitize_error(e), os.linesep))
    except Exception as e:
        clean_e = ams_schedule_lld.AMSZabbix.sanitize_error(e)
        ams_logger.error("Caught an exception running {}: {}".format(__file__, clean_e))
        ams_logger.error("Traceback: " + traceback.format_exc())
        _print_or_store('Failed to generate LLD: {}'.format(clean_e))
    finally:
        if email:
            _send_mail(email)
        else:
            ams_logger.info("No email configured so not sending email")
