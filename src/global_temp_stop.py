#!/usr/bin/python

import os.path
import sys
import ConfigParser
import getopt
import subprocess
from datetime import datetime

APP_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(APP_PATH)

from lib.Signals import Signal
from lib.Exceptions import SignalException
from lib.Helpers import CommTicketCommentOnlyHelper, UpdateBatchStatus, RunDate

available_groups = [
    'AFTER_HOURS_WORK',
    'FILE_ISSUES',
    'TWMNT',
    'MANUAL',
    'DUPLICATE_CHECK',
    'DUPLICATE_CHECK_COMPLETE',
    'ONE_AND_STOP',
    'TOO_MANY_FILES',
    'MISSING_MANIFEST',
    'TOO_MANY_MANIFESTS',
]

group_to_batch_status_map = {
    'TWMNT': 'TEMP_STOP_ON_TWMNT',
    'DUPLICATE_CHECK': 'TEMP_STOP_ON',
    'MANUAL': 'TEMP_STOP_ON',
    'DUPLICATE_CHECK_COMPLETE': 'TEMP_STOP_OFF',
    'ONE_AND_STOP': 'ONE_AND_STOP',
}

# set some defaults / setup some config data
config = ConfigParser.ConfigParser()
config.read(APP_PATH + '/Config/ssod_validator.cfg')
if not config.has_option('DEFAULT', 'global_temp_stop_signal'):
    raise SignalException('global_temp_stop_signal does not exist in config')

if not config.has_option('DEFAULT', 'base_automation_signal_path'):
    raise SignalException('No base automation signal path in config.')

temp_stop_filename = config.get('DEFAULT', 'global_temp_stop_signal')
temp_stop_filename_tmp, temp_stop_extension_tmp = os.path.splitext(temp_stop_filename)
global_temp_stop_signal = Signal(os.path.dirname(temp_stop_filename), os.path.basename(temp_stop_filename), True, temp_stop_extension_tmp)

def print_usage():
    """ This method will print the usage of the ssodETLProcess.py file
    :return: none
    """
    print '[USAGE1] python global_temp_stop.py -c <on|off> -g <group> -m <message>'
    print '[USAGE2] python global_temp_stop.py -c on -g AFTER_HOURS_WORK -m \'Re-indexing SOLR\''
    print 'Available Groups:' + os.linesep
    print os.linesep.join(available_groups)
    sys.exit(2)

def get_cur_user():
    cur_user = os.environ.get('_USER')
    if not cur_user:
        who_am_i = subprocess.Popen('whoami', stdout=subprocess.PIPE)
        cur_user = str(who_am_i.communicate()[0]).strip()

    return cur_user

def temp_stop_off():
    try:
        if not global_temp_stop_signal.exists():
            print '[SUCCESS] Temp Stop Signal Did Not Exist'
            return True

        if not global_temp_stop_signal.remove_signal():
            print '[FAILED] Could not remove signal for unknown reason.'
            return False

        sig_data = dict()
        sig_data['USER'] = get_cur_user()
        sig_data['GROUP'] = 'REMOVE_TEMP_STOP'
        sig_data['MESSAGE'] = 'Removing temp stop.'
        sig_data['DATE'] = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        sig_data_str = format_msg(sig_data, False)

        run_date = RunDate('dailycycle_transaction_date', 'transaction_dates_processed')
        run_date.get_current_run_date()

        batch_status = UpdateBatchStatus()
        batch_status.update_batch_status(os.path.basename(__file__), 'TEMP_STOP_OFF', sig_data['MESSAGE'], run_date.current_run_date)

        comm_ticket_comment = CommTicketCommentOnlyHelper()
        comm_ticket_comment.set_parameters(global_temp_stop_signal.full_file_path, sig_data_str)
        comm_ticket_comment.send_zabbix_message()
        print '[UPDATED COMMUNICATIONS TICKET] Using JIBBIX to update comms ticket with message.'
    except Exception as e:
        print '[FAILED] Caught exception removing signal: ' + str(e)
        return False

    print '[REMOVED SIGNAL] ' + global_temp_stop_signal.full_file_path

    return True

def temp_stop_on(msg, grp):
    try:
        sig_data = dict()
        sig_data['USER'] = get_cur_user()
        sig_data['GROUP'] = grp
        sig_data['MESSAGE'] = msg
        sig_data['DATE'] = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        sig_data_str = format_msg(sig_data, True)

        res = global_temp_stop_signal.write_signal_and_data(sig_data_str)

        if not res:
            print '[FAILED] Could not write signal for unknown reason.'
            return False

        print '[ADDED SIGNAL] ' + global_temp_stop_signal.full_file_path

        run_date = RunDate('dailycycle_transaction_date', 'transaction_dates_processed')

        status_group = 'TEMP_STOP_ON'
        if grp in group_to_batch_status_map:
            status_group = group_to_batch_status_map[grp]
        batch_status = UpdateBatchStatus()
        run_date.get_current_run_date()
        batch_status.update_batch_status(os.path.basename(__file__), status_group, sig_data['MESSAGE'], run_date.current_run_date)

        comm_ticket_comment = CommTicketCommentOnlyHelper()
        comm_ticket_comment.set_parameters(global_temp_stop_signal.full_file_path, sig_data_str)
        comm_ticket_comment.send_zabbix_message()
        print '[UPDATED COMMUNICATIONS TICKET] Using JIBBIX to update comms ticket with message.'
    except Exception as e:
        print '[FAILED] Caught exception writing signal: ' + str(e)
        return False

    return True

def format_msg(data, on_off_bool):
    ret_data = data['USER']
    if on_off_bool:
        ret_data += ' has placed the temporary stop on batch'
    else:
        ret_data += ' has removed the temporary stop on batch'

    ret_data += ' at ' + data['DATE'] + ' EDT.  The reason ' + data['USER'] + ' has given is (' + data['GROUP'] + '): ' + data['MESSAGE'] + '.'
    return ret_data.replace('..', '.')

def is_group_valid(group_input):
    if group_input not in available_groups:
        raise Exception('Group not allowed.  \'' + group_input + '\' not in \'' + ", ".join(available_groups) + '\'')

    return True

def main(argv):
    """ This is the main run process for global temp stop.
    :param argv: array
    :return: none
    """

    command = None
    group = None
    message = None

    try:
        opts, args = getopt.getopt(argv, "hc:g:m:")
        for opt, arg in opts:
            if opt == '-h':
                print_usage()
            elif opt == "-c":
                command = str(arg).strip()
            elif opt == "-g":
                group = str(arg).strip().upper()
            elif opt == "-m":
                message = str(arg).strip()

        if not command:
            print_usage()

        if command == 'on':
            if not group or not message:
                print_usage()
            is_group_valid(group)
            temp_stop_on(message, group)
        elif command == 'off':
            temp_stop_off()

    except getopt.GetoptError as e:
        # throw error on any get options error.
        print '[INVALID OPTION(S)] ' + str(e)
        print_usage()
    except Exception as e:
        print '[FAILED OPERATION] ' + str(e)

# this is how we invoke the main method to start everything off and we pass in argv from sys.
if __name__ == "__main__":
    main(sys.argv[1:])