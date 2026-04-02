#!/usr/bin/python

import getopt
import os.path
import sys
import traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(APP_PATH)

from lib.Exceptions import EmailException, EmailSuccessException, EmailSkipException
from EmailTemplates import AbstractEmailTemplate

# noinspection PyUnresolvedReferences
from EmailTemplates.Templates import *
from lib.Helpers import ProcCheck

def print_usage():
    """ This method will print the usage of the email_controller.py file
    :return: none
    """
    print '[USAGE1] python email_controller.py -e <email> -c <mail|test> -l <list of email addresses> -m <market name> -d <true|false> -f <true|false>'
    print '[USAGE2] python email_controller.py -e FileReport -c mail -l \'owen.hoyt@sas.com,owen.hoyt@sas.com\' -m \'Central America\' -d true'
    print '[NOTE] *** use -f true (force) to force the script to run without doing a proc check.  Do NOT schedule this in cron with -f otherwise multiple instances will be running concurrently'
    sys.exit(2)

def init_args(mail_template, cmd, email_list, market_name, subject, debug):
    try:
        # validator_to_call().validate()
        email_obj = globals()[mail_template](debug)  # type: AbstractEmailTemplate
        getattr(email_obj, 'init_email')
    except Exception as e:
        raise EmailException('Could not call email ' + mail_template + ': ' + str(e))

    if cmd == 'mail':
        print '[CONTROLLER] starting email...'
        email_obj.init_email(email_list, market_name, False, subject)
    elif cmd == 'test':
        print '[CONTROLLER] output only...'
        email_obj.init_email(email_list, market_name, True, subject)
    else:
        raise EmailException('Invalid command given: ' + cmd)

def main(argv):
    """ This is the main run process for SSOD emails.
    :param argv: array
    :return: none
    """
    # set some defaults for file paths.
    email_str = None
    command = None
    debug = False
    force = False
    proc_check = None  # type: ProcCheck
    exit_val = 0
    email_list = None
    market_name = None
    subject = None

    # start the proc check to ensure that this script cannot possibly run more than once at a time

    # try to determine the input arguments.
    try:
        opts, args = getopt.getopt(argv, "he:c:l:m:d:f:s:")
        for opt, arg in opts:
            if opt == '-h':
                print_usage()
            elif opt == "-e":
                email_str = arg
            elif opt == "-c":
                command = arg
            elif opt == "-l":
                email_list = str(arg).strip().lower()
            elif opt == "-m":
                market_name = str(arg).strip().title()
            elif opt == "-d" and str(arg).strip().lower() == 'true':
                debug = True
            elif opt == "-f" and str(arg).strip().lower() == 'true':
                force = True
            elif opt == "-s":
                subject = arg.strip()

        if not email_str or not command or not email_list or not market_name:
            print_usage()

        if force:
            print '[FORCE] You are overriding the proc check.  Please be sure no other ' + str(email_str) + ' emails are running and / or are commented out in CRON'
            print '[FORCE] Sleeping for 7 seconds while you decide.  \'ctrl+c\' to cancel...'
            # for s in range (1, 7):
            #     print '[FORCE] ' + str(s) + '...'
            #     time.sleep(1)
        else:
            # initiate the proc check.
            proc_check = ProcCheck(__file__, os.getpid(), email_str)
            # add extra grep string of the current email.
            proc_check.add_extra_grep(email_str)
            # check to see if this email is already running.
            proc_check.am_i_already_running()

        init_args(email_str, command, email_list, market_name, subject, debug)
    except getopt.GetoptError as e:
        # throw error on any get options error.
        print '[INVALID OPTION(S)] ' + str(e)
        print_usage()
    except EmailException as e:
        print '--------------------------------------------------'
        print str(e)
        print '--------------------------------------------------'
        if debug:
            traceback.print_exc()
        exit_val = 2
    except EmailSuccessException:
        print '[SUCCESS] ' + command + ' for email ' + email_str
        exit_val = 0
    except EmailSkipException as e:
        print '[SKIP] ' + str(e)
    except Exception as e:
        print '[ERROR]: ' + str(e)
        if debug:
            traceback.print_exc()
        exit_val = 2
    finally:
        print '[CONTROLLER] Deleting lock file...'
        if proc_check:
            proc_check.delete_lock_file()
        print '[CONTROLLER] Exiting...'
        sys.exit(exit_val)

# this is how we invoke the main method to start everything off and we pass in argv from sys.
if __name__ == "__main__":
    main(sys.argv[1:])
