#!/usr/bin/python

import getopt
import os.path
import sys
import traceback
from datetime import datetime
import time

APP_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(APP_PATH)

from lib.Exceptions import AutomationException, AutomationSuccessException, SkipAutomationException
from Automation import AbstractAutomation

# noinspection PyUnresolvedReferences
from Automation.Automations import *
from lib.Helpers import ProcCheck

def print_usage():
    """ This method will print the usage of the ssodETLProcess.py file
    :return: none
    """
    print '[USAGE1] python automation_controller.py -a <automation> -c <run|status|temp-stop-on|temp-stop-off|clear-signals|resume> -d <true|false> -f <true|false>'
    print '[USAGE2] python automation_controller.py -a USDReport -c run -d true'
    print '[NOTE] *** use -f true (force) to force the script to run without doing a proc check.  Do NOT schedule this in cron with -f otherwise multiple instances will be running concurrently'
    sys.exit(2)

def init_args(auto, cmd, debug):
    try:
        # validator_to_call().validate()
        automation_obj = globals()[auto](debug)  # type: AbstractAutomation
        getattr(automation_obj, 'start_automation')
    except Exception as e:
        raise AutomationException('Could not call automation ' + auto + ': ' + str(e))

    if cmd == 'run':
        print '[CONTROLLER] starting automation...'
        automation_obj.start_automation()
    elif cmd == 'clear-signals':
        print '[CONTROLLER] Clearing Signals...'
        automation_obj.clear_signals()
    elif cmd == "status":
        raise AutomationException('status command has not been implemented yet')
    elif cmd == "temp-stop-on":
        print '[CONTROLLER] Creating temp stop signal specific to ' + str(automation_obj) + ' automation...'
        automation_obj.init_signals()
        automation_obj.temp_stop_signal.write_signal_and_data('Putting temp stop on per automation_controller.py at ' + str(datetime.now()))
        print '[CONTROLLER] Temp stop is now on: ' + automation_obj.temp_stop_signal.signal_path
    elif cmd == "temp-stop-off":
        print '[CONTROLLER] Removing temp stop signal specific to ' + str(automation_obj) + ' automation...'
        automation_obj.init_signals()
        automation_obj.temp_stop_signal.remove_signal()
        print '[CONTROLLER] Temp stop has been removed: ' + automation_obj.temp_stop_signal.signal_path
    elif cmd == 'resume':
        print '[CONTROLLER] resuming automation...'
        automation_obj.remove_stopped()
        automation_obj.start_automation()
    else:
        raise AutomationException('Invalid command given: ' + cmd)

def main(argv):
    """ This is the main run process for SSOD automations.
    :param argv: array
    :return: none
    """
    # set some defaults for file paths.
    automation_str = None
    command = None
    debug = False
    force = False
    proc_check = None  # type: ProcCheck
    exit_val = 0

    # start the proc check to ensure that this script cannot possibly run more than once at a time

    # try to determine the input arguments.
    try:
        opts, args = getopt.getopt(argv, "ha:c:d:f:")
        for opt, arg in opts:
            if opt == '-h':
                print_usage()
            elif opt == "-a":
                automation_str = arg
            elif opt == "-c":
                command = arg
            elif opt == "-d" and str(arg).strip().lower() == 'true':
                debug = True
            elif opt == "-f" and str(arg).strip().lower() == 'true':
                force = True

        if not automation_str or not command:
            print_usage()

        if force:
            print '[FORCE] You are overriding the proc check.  Please be sure no other ' + str(automation_str) + ' automations are running and / or are commented out in CRON'
            print '[FORCE] Sleeping for 7 seconds while you decide.  \'ctrl+c\' to cancel...'
            for s in range (1, 7):
                print '[FORCE] ' + str(s) + '...'
                time.sleep(1)
        else:
            # initiate the proc check.
            proc_check = ProcCheck(__file__, os.getpid(), automation_str)
            # add extra grep string of the current automation.
            proc_check.add_extra_grep(automation_str)
            # check to see if this automation is already running.
            proc_check.am_i_already_running()

        init_args(automation_str, command, debug)
    except getopt.GetoptError as e:
        # throw error on any get options error.
        print '[INVALID OPTION(S)] ' + str(e)
        print_usage()
    except AutomationException as e:
        print '--------------------------------------------------'
        print str(e)
        print '--------------------------------------------------'
        if debug:
            traceback.print_exc()
        exit_val = 2
    except AutomationSuccessException:
        print '[SUCCESS] ' + command + ' for automation ' + automation_str
        exit_val = 0
    except SkipAutomationException as e:
        print '[CONTROLLER] skipped ' + command + ' for automation ' + automation_str
        print '[CONTROLLER]' + str(e)
        exit_val = 0
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
