import os
import sys
import argparse
import logging

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Config import AMSJibbixOptions
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Lib.Defaults import AMSDefaults


if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    ams_logger.set_debug(False)
    AMSDefaults = AMSDefaults()

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--tla", nargs='?', help="Three letter abb for project", required=True)
    arg_parser.add_argument("--comment", nargs='?', help="String you want to update ticket with", required=True)
    arg_parser.add_argument("--hostname", nargs='?', help="Enter hostname you'd like to update", required=False)
    arg_parser.add_argument("--zabbix_proxy", nargs='?', help="Zabbix proxy to use", required=False, default=AMSDefaults.zabbix_proxy)
    arg_parser.add_argument("--link", nargs='?', help="The ticket you'd like to update (default is comm)", required=False)
    arg_parser.add_argument("--security", nargs='?', help="The security level for the comment", required=False)
    args = arg_parser.parse_args(sys.argv[1:])

    tla = args.tla.strip()

    # jibbix option values to set comment
    AMSJibbixOptions = AMSJibbixOptions()
    AMSJibbixOptions.project = tla
    AMSJibbixOptions.comment_only = "yes"

    if args.link is not None:
        AMSJibbixOptions.link = args.link.strip()
    else:
        AMSJibbixOptions.link = "comm"

    if args.security is not None:
        AMSJibbixOptions.security = args.security.strip()

    if args.hostname is not None:
        hostname = args.hostname.strip()
        AMSZabbix = AMSZabbix(ams_logger,hostname=hostname)
    else:
        AMSZabbix = AMSZabbix(ams_logger)

    AMSZabbix.zabbix_proxy = args.zabbix_proxy.strip()

    ams_logger.info("Sending update to Zabbix...")

    # send update to zabbix
    result = AMSZabbix.call_zabbix_sender(AMSDefaults.default_zabbix_key_no_schedule, AMSJibbixOptions.str_from_options() + "\n" + args.comment)
    if not result:
        sys.exit(1)