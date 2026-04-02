import argparse
import logging
import sys
import time
import traceback
import readline
import getpass
from six.moves import input

import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Exceptions import AMSExceptionNoEventNotification, AMSValidationException, AMSZabbixException
from Toolkit.Lib.Defaults import AMSDefaults


def _get_credentials():
    readline.set_startup_hook(lambda: readline.insert_text(current_user))
    user = input('Enter Your Zabbix Username (VSP): ')
    readline.set_startup_hook()
    passwd = getpass.getpass('Enter Your Zabbix Password (VSP): ')
    return user, passwd

if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    current_user = AMSDefaults().current_user
    ams_defaults = AMSDefaults()

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--zabbix_url", nargs='?', type=str, help="Zabbix URL", required=False, default=ams_defaults.zabbix_url)
    # noinspection PyTypeChecker
    arg_parser.add_argument("--template_name", nargs='?', type=str, help="Zabbix Template Name", required=True)
    # noinspection PyTypeChecker
    arg_parser.add_argument("--hosts", nargs='?', type=str, help="List of hosts to apply template to", required=True)

    args = arg_parser.parse_args()
    ams_logger.set_debug(False)

    # if we don't pass in the host, we'll grab it from the config and it will be assumed to be the current host.
    ams_logger.debug('host={}'.format(ams_defaults.my_hostname))

    try:
        username, password = _get_credentials()
    except Exception as e:
        raise AMSValidationException('Failed to capture user credentials.')

    zabbix = AMSZabbix(ams_logger, None, username=username, password=password)
    zabbix.username = username
    zabbix.password = password
    zabbix.url = args.zabbix_url

    try:
        # Add template per host
        hosts = str(args.hosts).split(',')
        for host in hosts:
            host = host.strip()
            ams_logger.info('Applying template {} to host {}'.format(args.template_name, host))
            result = zabbix.apply_template_to_host(args.template_name, host, clear_cache=False)
            ams_logger.info('Result is {} for host {}'.format(result, host))

    except KeyboardInterrupt:
        ams_logger.error('{}User killed process with ctrl+c...'.format(os.linesep))
    except AMSExceptionNoEventNotification as e:
        ams_logger.error("{}Process exited with a AMSExceptionNoEventNotification exception: {}{}".format(os.linesep, AMSZabbix.sanitize_error(e), os.linesep))
    except Exception as e:
        ams_logger.error("Caught an exception running {}: {}".format(__file__, AMSZabbix.sanitize_error(e)))
        ams_logger.error("Traceback: " + traceback.format_exc())
