#!/usr/bin/env /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python

#########################################################
#
#  compare_date.py
#
#    reads dates from the file a text file
#    and compares them to today's date
#    and fails if the date in file is found in the list
#
#    Intended to be run as a trigger script
#
#    if today's date is found in the file:
#      - update the comm ticket with the fact that the schedule is being skipped
#      - exit with return code 1 to prevent the schedule from executing
#      - dates need to be in ccyy-mm-dd format in the file
#      - specific date can also be passed in using --disable_date
#
#    a signal directory must exist
#    /{tla}/projects/default/{tla}run/signal
#
#
# ===============================================
# |  2021-07-01 |  mihait | initial development |
# |             |         |                     |
# ===============================================
##########################################################


import os
import sys
import subprocess
import argparse
from datetime import date
from datetime import datetime
from os import path

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Config import AMSJibbixOptions


def main():
    defaults=AMSDefaults()
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    ams_logger.set_debug(False)

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--tla", nargs='?', help="Three letter abb for project", required=True)
    arg_parser.add_argument("--zabbix_proxy", nargs='?', help="Zabbix proxy to use", required=False,
                            default=defaults.zabbix_proxy)
    arg_parser.add_argument("--update_comm", nargs='?', help="Update comm ticket? y/n Default y", required=False,
                            default="y")
    arg_parser.add_argument("--in_file", nargs='?', help="File containing dates to disable schedule", required=False)
    arg_parser.add_argument("--disable_date", nargs='?', help="Single date to disable schedule", required=False)
    arg_parser.add_argument("--update_once", nargs='?', help="only update comm ticket once per day? y/n Default y", required=False, default="y")
    arg_parser.add_argument("--security", nargs='?', help="Zabbix security (sas/None) default None", required=False,
                            default="none")
    arg_parser.add_argument("--signal_dir", nargs='?', help="Should be /{tla}/projects/default/{tla}run/signal, required if update_once set to Y", required=False,
                            default="none")
    arg_parser.add_argument("--enable", nargs='?', help="y/n If y, the schedule will only execute on dates in the list.  Default n", required=False,
                            default="n")


    args = arg_parser.parse_args(sys.argv[1:])

    today = date.today().strftime("%Y-%m-%d")
    return_code = 0
    date_found = False
    update_once = True

    enable=check_yn_arg(args.enable, False)
    update_comm=check_yn_arg(args.update_comm, True)
    if update_comm:
        update_once=check_yn_arg(args.update_once, True)
    if update_comm and update_once:
        if args.signal_dir is not None:
            if path.exists(args.signal_dir):
                pass
            else:
                raise Exception("signal_dir does not exist")
        else:
            raise Exception("signal_dir required when update_comm and update_once are 'y'. Default for update once is 'y'")

    # date passed from command line takes precedent
    if args.disable_date is not None:
        date_found=find_date(args.disable_date, today)

    if not date_found:
        date_found=find_date_infile(args.in_file, today)

    if enable and date_found:
        #enable is set and date is found, so run the schedule
        return_code=0
    elif enable and not date_found:
        # enable is set and date not found, so dont run schedule
        # we dont update the comm ticket in this scenario because its
        # assumed this schedule does not typically run, only runs in a special case
        return_code=1
    elif not enable and not date_found:
        #disable is set and date not found, so run schedule
        return_code=0
    elif not enable and date_found:
        #disable is set and date found, so dont run schedule
        return_code=1
        if update_comm:
            add_comment(args.tla, args.security, args.zabbix_proxy, today, update_once, ams_logger, args.signal_dir)

    sys.exit(return_code)


def find_date_infile(date_list, today):

    date_found=False

    try:

        if date_list is not None:
            if path.isfile(date_list):
                with open(date_list) as f:
                    for line in f:
                        if line[0] == '#':
                            pass
                        else:
                            validate_date(line.strip())
                            if today == line.strip():
                                date_found=True
    except Exception as e:
        raise Exception('Problem with file {}: {}'.format(date_list, e))

    return date_found


def find_date(date_single, today):

    date_found=False

    try:
        validate_date(date_single)
        if today == date_single:
            date_found=True
    except Exception as e:
        raise Exception('Problem with disable_date: {}'.format(e))

    return date_found


def add_comment(tla, security, proxy, today, update_once, ams_logger, signal):

    #check if sig file exists
    sig_file=os.path.join(signal, "date_disable_comm_update.sig")
    create_jira = False

    if not update_once:
        create_jira = True
    else:
        if not path.isfile(sig_file):
            create_sig(sig_file, today)
            create_jira = True
        else:
            if get_file_age(sig_file) != today:
                remove_sig(sig_file)
                create_sig(sig_file, today)
                create_jira = True

    if create_jira:

        jibbix = AMSJibbixOptions()
        jibbix.project = tla
        jibbix.comment_only = "yes"
        jibbix.link = "comm"
        jibbix.security = security
        zabbix = AMSZabbix(ams_logger)
        zabbix.zabbix_proxy = proxy

        ams_logger.info("Sending update to Zabbix...")
        ticket_comment="'Schedule skipped for {}'".format(today)

        defaults=AMSDefaults()
        zabbix.call_zabbix_sender(defaults.default_zabbix_key_no_schedule,
                                     jibbix.str_from_options() + "\n" + ticket_comment)


def create_sig(sig_file,today):
    #create the file with today's date
    try:
        f = open(sig_file, "w")
        f.write(today)
        f.close()
    except IOError as e:
        raise Exception('Problem creating sig file {}: {}'.format(sig_file,e))


def get_file_age(sig_file):
    #get the date in the file
    try:
        with open(sig_file, "r") as sig:
            return sig.read()
    except IOError as e:
        raise Exception('Problem reading sig file {}: {}'.format(sig_file,e))
    finally:
        sig.close()


def remove_sig(sig_file):
    # removing the sig file
    try:
        if not os.remove(sig_file):
            pass
    except IOError as e:
        raise Exception('Problem removing old signal file {}: {}'.format(sig_file, e))


def validate_date(test_str):
    try:
        datetime.strptime(test_str.strip(), '%Y-%m-%d')
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DD")


def check_yn_arg(arg, default):
    if arg == 'Y' or arg == 'y':
        value=True
    elif arg == 'N' or arg == 'n':
        value=False
    else:
        value=default

    return value

if __name__ == "__main__":
    main()

