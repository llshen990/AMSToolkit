import os
import sys
import argparse

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Config import AMSJibbixOptions
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Lib.Defaults import AMSDefaults


def _parse_args(args=None, ams_defaults=None):

    arg_parser = argparse.ArgumentParser(
        fromfile_prefix_chars='@'
    )

    # noinspection PyTypeChecker
    arg_parser.add_argument(
        "--tla",
        type=str,
        help="Three letter abb for project",
        required=True
    )

    arg_parser.add_argument(
        "--comment",
        type=str,
        help="String you want to update ticket with",
        required=False
    )

    arg_parser.add_argument(
        "--hostname",
        type=str,
        help="Enter hostname you'd like to update (default: %(default)s)",
        default=ams_defaults.my_hostname,
        required=False
    )

    arg_parser.add_argument(
        "--zabbix_proxy",
        type=str,
        help="Zabbix proxy to use (default: %(default)s)",
        required=False,
        default=ams_defaults.zabbix_proxy
    )

    arg_parser.add_argument(
        "--link",
        type=str,
        help="The ticket you'd like to update (leave blank for new ticket)",
        required=False
    )

    arg_parser.add_argument(
        "--security",
        choices=['none', 'sas', 'sso'],
        help="The security level for the comment. (default: %(default)s)",
        required=False,
        default='none'
    )

    arg_parser.add_argument(
        "--type",
        type=str,
        help="The type of ticket, (default: %(default)s)",
        required=False,
        default='issue'
    )

    arg_parser.add_argument(
        "--priority",
        choices=['blocker', 'critical', 'major', 'minor', 'trivial'],
        help="Ticket priority (default: %(default)s)",
        required=False,
        default='critical'
    )

    arg_parser.add_argument(
        "--assignee",
        type=str,
        help="Assign ticket to user. Leave blank for default assignee",
        required=False
    )

    arg_parser.add_argument(
        "--summary",
        type=str,
        help="Summary for ticket",
        required=False
    )

    arg_parser.add_argument(
        "--merge",
        help="Merge new alerts into last open ticket (default: %(default)s)",
        choices=['no', 'yes', 'simple', 'skip'],
        default='no',
        required=False
    )

    arg_parser.add_argument(
        "--description",
        help="Jira ticket Description",
        type=str,
        required=False
    )

    # CLDOE-74
    arg_parser.add_argument(
        "--bundle",
        help="Adds comment to an existing ticket with this same bundle string. Expires after bundle_time",
        type=str,
        required=False
    )

    arg_parser.add_argument(
        "--bundle_time",
        help="The number of seconds to persist bundling tickets with the same bundle string.",
        type=int,
        required=False
    )

    arg_parser.add_argument(
        "--component",
        help="All component values are supported as long as they are allowed for the project in JIRA",
        type=str,
        required=False
    )

    arg_parser.add_argument(
        "--labels",
        help="Comma seperated list of labels",
        type=str,
        required=False
    )

    arg_parser.add_argument(
        "--watchers",
        help="Comma seperated list of JIRA user IDs",
        type=str,
        required=False
    )

    arg_parser.add_argument(
        "--notify",
        help="If ticket fails to open, try again using ZABIX as project value",
        required=False
    )

    arg_parser.add_argument(
        "--commentOnly",
        choices=['no', 'Yes'],
        help="Don\'t open a ticket, only add descriptions a comment to the linked ticket (default: %(default)s)",
        required=False,
        default='no')

    return arg_parser.parse_args()


def _process_args(args):
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')

    if (args.comment or args.description) is None:
        print('One of [comment, description] is required and neither were provided.')
        exit(1)

    # jibbix option values to set comment
    ams_jibbix = AMSJibbixOptions()
    ams_jibbix.project = args.tla

    if args.link is not None:
        ams_jibbix.link = args.link
    else:
        ams_jibbix.link = "none"

    ams_jibbix.type = args.type
    ams_jibbix.priority = args.priority
    ams_jibbix.security = args.security
    ams_jibbix.comment = args.comment
    ams_jibbix.description = args.description

    if args.link is not None:
        ams_jibbix.link = args.link
    else:
        ams_jibbix.link = "none"

    ams_jibbix.merge = args.merge

    if args.summary is not None:
        ams_jibbix.summary = args.summary

    if args.assignee is not None:
        ams_jibbix.assignee = args.assignee

    if args.hostname is not None:
        ams_zabbix = AMSZabbix(ams_logger, hostname=args.hostname)
    else:
        ams_zabbix = AMSZabbix(ams_logger)

    if args.bundle is not None:
        ams_jibbix.bundle = args.bundle
        if args.bundle_time is not None:
            ams_jibbix.bundle_time = args.bundle_time
        else:
            ams_jibbix.bundle_time = 360

    if args.component is not None:
        ams_jibbix.component = args.component

    if args.labels is not None:
        ams_jibbix.labels = args.labels

    if args.watchers is not None:
        ams_jibbix.watchers = args.watchers

    if args.notify is not None:
        ams_jibbix.notify = args.notify

    ams_zabbix.zabbix_proxy = args.zabbix_proxy

    return ams_jibbix, ams_zabbix


def main(args=None):
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    ams_defaults = AMSDefaults()
    args = _parse_args(args, ams_defaults)
    ams_jibbix, ams_zabbix = _process_args(args)
    ams_logger.info("Sending update to Zabbix...")

    # send update to zabbix
    result = ams_zabbix.call_zabbix_sender(ams_defaults.default_zabbix_key_no_schedule,
                                          ams_jibbix.str_from_options())
    if not result:
        print("Failed to send send jibbix message to Zabbix")
        sys.exit(1)
    else:
        print("Jibbix message sent to Zabbix")


if __name__ == "__main__":
    main()

    # ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    # AMSDefaults = AMSDefaults()

    # arg_parser = argparse.ArgumentParser()
    # # noinspection PyTypeChecker
    # arg_parser.add_argument("--tla", type=str, help="Three letter abb for project", required=True)
    # arg_parser.add_argument("--comment", type=str, help="String you want to update ticket with", required=False)
    # arg_parser.add_argument("--hostname", type=str, help="Enter hostname you'd like to update (default: %(default)s)", default=AMSDefaults.my_hostname, required=False)
    # arg_parser.add_argument("--zabbix_proxy", type=str, help="Zabbix proxy to use (default: %(default)s)", required=False, default=AMSDefaults.zabbix_proxy)
    # arg_parser.add_argument("--link", type=str, help="The ticket you'd like to update (leave blank for new ticket)", required=False)
    # arg_parser.add_argument("--security", choices=['none', 'sas', 'sso'], help="The security level for the comment. (default: %(default)s)", required=False, default='none')
    # arg_parser.add_argument("--type", type=str, help="The type of ticket, (default: %(default)s)", required=False, default='issue')
    # arg_parser.add_argument("--priority", choices=['blocker', 'critical', 'major', 'minor', 'trivial'], help="Ticket priority (default: %(default)s)", required=False, default='critical')
    # arg_parser.add_argument("--assignee", type=str, help="Assign ticket to user. Leave blank for default assignee", required=False)
    # arg_parser.add_argument("--summary", type=str, help="Summary for ticket", required=False)
    # arg_parser.add_argument("--merge", help="Merge new alerts into last open ticket (default: %(default)s)", choices=['no', 'yes', 'simple', 'skip'], default='no', required=False)
    # arg_parser.add_argument('--description', help='Jira ticket Description', type=str, required=False)
    # # CLDOE-74
    # arg_parser.add_argument('--bundle', help='Adds this ticket as a comment to an existing ticket with this same bundle string. Expires after bundle_time reached (default 360 seconds)', type=str, required=False)
    # arg_parser.add_argument('--bundle_time', help='', type=int, required=False)
    # arg_parser.add_argument('--component', help='All component values are supported as long as they are allowed for the project in JIRA', type=str, required=False )
    # arg_parser.add_argument('--labels', help='Comma seperated list of Labels', type=str, required=False)
    # arg_parser.add_argument('--watchers', help='Comma seperated list of JIRA user IDs', type=str, required=False)
    # arg_parser.add_argument('--notify', help='If ticket fails to open, try again using ZABIX as project value', required=False)
    # arg_parser.add_argument('--commentOnly', help='Don\'t open a ticket, only add descriptions a comment to the linked ticket (Yes/no) Default no',
    #                         required=False, default='no')
    # args = arg_parser.parse_args

    # if (args.comment or args.description) is None:
    #     arg_parser.print_help()
    #     print('One of [comment, description] is required and neither were provided.')
    #     exit(1)
    #
    # tla = args.tla
    #
    # # jibbix option values to set comment
    # AMSJibbixOptions = AMSJibbixOptions()
    # AMSJibbixOptions.project = tla
    #
    #
    # if args.link is not None:
    #    AMSJibbixOptions.link = args.link
    # else:
    #    AMSJibbixOptions.link = "none"
    #
    # AMSJibbixOptions.type = args.type
    #
    # AMSJibbixOptions.priority = args.priority
    #
    # AMSJibbixOptions.security = args.security
    #
    # AMSJibbixOptions.comment = args.comment
    #
    # AMSJibbixOptions.description = args.description
    #
    # if args.link is not None:
    #     AMSJibbixOptions.link = args.link
    # else:
    #     AMSJibbixOptions.link = "none"
    #
    # AMSJibbixOptions.merge = args.merge
    #
    # if args.summary is not None:
    #     AMSJibbixOptions.summary = args.summary
    #
    # if args.assignee is not None:
    #     AMSJibbixOptions.assignee = args.assignee
    #
    # if args.hostname is not None:
    #     hostname = args.hostname
    #     AMSZabbix = AMSZabbix(ams_logger, hostname=hostname)
    # else:
    #     AMSZabbix = AMSZabbix(ams_logger)
    #
    # if args.bundle is not None:
    #     AMSJibbixOptions.bundle = args.bundle
    #     if args.bundle_time is not None:
    #         AMSJibbixOptions.bundle_time = args.bundle_time
    #     else:
    #         AMSJibbixOptions.bundle_time = 360
    #
    # if args.component is not None:
    #     AMSJibbixOptions.component = args.component
    #
    # if args.labels is not None:
    #     AMSJibbixOptions.labels = args.labels
    #
    # if args.watchers is not None:
    #     AMSJibbixOptions.watchers = args.watchers
    #
    # if args.notify is not None:
    #     AMSJibbixOptions.notify = args.notify
    #
    # AMSZabbix.zabbix_proxy = args.zabbix_proxy

    # ams_logger.info("Sending update to Zabbix...")
    #
    # # send update to zabbix
    # result = AMSZabbix.call_zabbix_sender(AMSDefaults.default_zabbix_key_no_schedule, AMSJibbixOptions.str_from_options())
    # if not result:
    #     print("Failed to send send jibbix message to Zabbix")
    #     sys.exit(1)
    # else:
    #     print("Jibbix message sent to Zabbix")
