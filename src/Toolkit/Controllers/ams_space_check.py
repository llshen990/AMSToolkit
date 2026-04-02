# Create utility to generate disk usage report
# from Toolkit.Lib.AMSSpaceChecker import AMSSpaceChecker
# This is just a main function, need to import class AMSSpaceChecker
# Usage:ams_space_check.py --file_system=<FILE_SYSTEM> --tla=<TLA> --dir_topn=<> --file_topn=<> [Other options]


import argparse
import logging
import sys
import os
import traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.AMSSpaceChecker import AMSSpaceChecker
from datetime import date,datetime,timedelta
from Toolkit.Lib import AMSLogger
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Config import AMSJibbixOptions
from Toolkit.Lib.Defaults import AMSDefaults

if __name__ == '__main__':
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    AMSDefaults = AMSDefaults()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--file_system",nargs='?', type=str, help="On which disk to check space usage", required=True)
    # arg_parser.add_argument("--jira_ticket",nargs='?', type=str,help="Jira Ticket", required=False)
    arg_parser.add_argument("--tla", nargs='?', help="Three letter abb for project", required=True)
    arg_parser.add_argument("--dir_topn", nargs='?', type=int, help="Top n directories in space consumption", required=False,default=10)
    arg_parser.add_argument("--file_topn", nargs='?', type=int, help="Top n files in file size", required=False,default=25)
    arg_parser.add_argument("--days", nargs='?', type=int, help="Top directories and files in space consumption modified in the past n days", required=False,default=1)
    # arg_parser.add_argument("--comment", nargs='?', help="String you want to update ticket with", required=True)
    arg_parser.add_argument("--new_ticket", nargs='?', type=bool, help="Do you want to create a new ticket?", required=False, default=False)
    arg_parser.add_argument("--hostname", nargs='?', help="Enter hostname you'd like to update", required=False)
    arg_parser.add_argument("--zabbix_proxy", nargs='?', help="Zabbix proxy to use", required=False,
                            default=AMSDefaults.zabbix_proxy)
    arg_parser.add_argument("--link", nargs='?', help="The ticket you'd like to update (leave blank for new ticket)",
                            required=False)
    arg_parser.add_argument("--security", nargs='?',
                            help="The security level for the comment. Default none (none, sas, sso)", required=False)
    arg_parser.add_argument("--type", nargs='?', help="The type of ticket, default is issue", required=False)
    arg_parser.add_argument("--priority", nargs='?',
                            help="blocker, critical, major, minor, trivial (default is critical)", required=False)
    arg_parser.add_argument("--assignee", nargs='?', help="Assign ticket to user. Leave blank for default assignee",
                            required=False)
    arg_parser.add_argument("--summary", nargs='?', help="Summary for ticket", required=False)

    args = arg_parser.parse_args(sys.argv[1:])

    file_system=args.file_system

    AMSJibbixOptions = AMSJibbixOptions()
    AMSJibbixOptions.project = args.tla.strip()
    if args.new_ticket == True:
        if args.link is not None:
            AMSJibbixOptions.link = args.link.strip()
        else:
            AMSJibbixOptions.link = "none"

        if args.type is not None:
            AMSJibbixOptions.type = args.type.strip()
        else:
            AMSJibbixOptions.type = "issue"

        if args.priority is not None:
            AMSJibbixOptions.priority = args.priority.strip()
        else:
            AMSJibbixOptions.priority = "critical"

        if args.security is not None:
            AMSJibbixOptions.security = args.security.strip()
        else:
            AMSJibbixOptions.security = "none"

        if args.summary is not None:
            AMSJibbixOptions.summary = args.summary.strip()

        if args.assignee is not None:
            AMSJibbixOptions.assignee = args.assignee.strip()

        if args.hostname is not None:
            hostname = args.hostname.strip()
            AMSZabbix = AMSZabbix(ams_logger, hostname=hostname)
        else:
            AMSZabbix = AMSZabbix(ams_logger)
    else:
        AMSJibbixOptions.comment_only = "yes"

        if args.link is not None:
            AMSJibbixOptions.link = args.link.strip()
        else:
            AMSJibbixOptions.link = "comm"

        if args.security is not None:
            AMSJibbixOptions.security = args.security.strip()

        if args.hostname is not None:
            hostname = args.hostname.strip()
            AMSZabbix = AMSZabbix(ams_logger, hostname=hostname)
        else:
            AMSZabbix = AMSZabbix(ams_logger)

    AMSZabbix.zabbix_proxy = args.zabbix_proxy.strip()
    comment = ""
    try:
        dsc_chk=AMSSpaceChecker(file_system)
        dsc_chk.m_days=args.days
        dsc_chk.top_n_dirlist=args.dir_topn
        dsc_chk.top_n_files=args.file_topn
        dsc_chk.exclude_dirs=[]
        dsc_chk.find_dirs_and_files(file_system,dsc_chk.m_days,dsc_chk.exclude_dirs)
        result1=dsc_chk.get_large_files(dsc_chk.files,dsc_chk.top_n_files)
        result2=dsc_chk.get_large_dirs(dsc_chk.dirlist,dsc_chk.top_n_dirlist)
        result3=dsc_chk.get_large_files(dsc_chk.files,dsc_chk.top_n_files)
        result4=dsc_chk.get_large_dirs(dsc_chk.dirlist,dsc_chk.top_n_dirlist)


        head = "Files and directories space comsumption in "+ str(file_system)+":"+ os.linesep + os.linesep
        print head
        str1 = "Top " + str(dsc_chk.top_n_files) + " files in file size" + os.linesep
        comment += head + str1
        print os.linesep + str1
        for item in result1:
            comment += str(item).strip('[]').replace('\'','')+ os.linesep
            print str(item).strip('[]').replace('\'','')

        str2 = "Top " +str(dsc_chk.top_n_dirlist) + " directories in space consumption "
        print os.linesep + str2
        comment += os.linesep + str2 + os.linesep
        for item in result2:
            comment += str(item).strip('[]').replace('\'','')+ os.linesep
            print str(item).strip('[]').replace('\'','')

        str3 = "Top " + str(dsc_chk.top_n_files) +" files in file size that have been modified in the past " + str(dsc_chk.m_days) + " days."
        print os.linesep + str3
        comment += os.linesep + str3 + os.linesep
        for item in result3:
            comment += str(item).strip('[]').replace('\'','')+ os.linesep
            print str(item).strip('[]').replace('\'','')

        str4 = "Top " + str(dsc_chk.top_n_dirlist)+" directories in space consumption of files modified in the past "+str(dsc_chk.m_days)+" days. "
        print os.linesep + str4
        comment += os.linesep + str4 + os.linesep

        for item in result4:
            comment += str(item).strip('[]').replace('\'','')+ os.linesep
            print str(item).strip('[]').replace('\'','')

        print os.linesep + comment
    except Exception as e:
        ams_logger.error("Error occurred while executing AMSSpaceChecker: %s" % str(e))
        ams_logger.error("Traceback: " + traceback.format_exc())

    ams_logger.info("Sending update to Zabbix...")
    ams_logger.debug('file_sysytem=%s' % str(args.file_system).strip())

    result = AMSZabbix.call_zabbix_sender(AMSDefaults.default_zabbix_key_no_schedule,
                                          AMSJibbixOptions.str_from_options() + "\n" + comment)
    if not result:
        print("Failed to send send jibbix message to Zabbix")
        sys.exit(1)
    else:
        print("Jibbix message sent to Zabbix")
