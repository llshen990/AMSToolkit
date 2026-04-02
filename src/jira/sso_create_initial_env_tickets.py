#!/usr/bin/python

import os.path, sys, getopt, traceback, csv, json

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from classes.jibbix import *

run_password_default = 'ASDFljc0234lcj'
server_fqdn = None  # type: str
csv_file_path = None  # type: str
master_jira_ticket = None  # type: str
run_password = None  # type: str
num_cols_expected_in_csv = 7
default_assignee = 'owhoyt'
environment_config = {
    'wbr01au.vsp.sas.com': {
        'HOST': 'wbr01au.vsp.sas.com',
        'HOST_SHORT': 'wbr01au',
        'TLA': 'WBR',
        'TLA_LOWER_CASE': 'wbr',
        'ENV': 'DEV',
        'DB_SERVICE': 'wbrdev01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'wbrdev01',
        'MARKET_NAME': 'Argentina',
        'VA_SERVER': 'wbr02au.vsp.sas.com',
        'RUN_USER': 'wbrrun',
        'RUN_PATH': '/wbr/projects/fcs/wbrrun',
    },
    'wbr03au.vsp.sas.com': {
        'HOST': 'wbr03au.vsp.sas.com',
        'HOST_SHORT': 'wbr03au',
        'TLA': 'WBR',
        'TLA_LOWER_CASE': 'wbr',
        'ENV': 'TEST',
        'DB_SERVICE': 'wbrtst01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'wbrtst01',
        'MARKET_NAME': 'Argentina',
        'VA_SERVER': 'wbr04au.vsp.sas.com',
        'RUN_USER': 'wbrrun',
        'RUN_PATH': '/wbr/projects/fcs/wbrrun',
    },
    'wbr07au.vsp.sas.com': {
        'HOST': 'wbr07au.vsp.sas.com',
        'HOST_SHORT': 'wbr07au',
        'TLA': 'WBR',
        'TLA_LOWER_CASE': 'wbr',
        'ENV': 'PROD',
        'DB_SERVICE': 'wbrprd01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'wbrprd01',
        'MARKET_NAME': 'Argentina',
        'VA_SERVER': 'wbr08au.vsp.sas.com',
        'RUN_USER': 'wbrrun',
        'RUN_PATH': '/wbr/projects/fcs/wbrrun',
    },
    'win05au.vsp.sas.com': {
        'HOST': 'win05au.vsp.sas.com',
        'HOST_SHORT': 'win05au',
        'TLA': 'WIN',
        'TLA_LOWER_CASE': 'win',
        'ENV': 'DEV',
        'DB_SERVICE': 'windev01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'windev01',
        'MARKET_NAME': 'China',
        'VA_SERVER': 'win06au.vsp.sas.com',
        'RUN_USER': 'winrun',
        'RUN_PATH': '/win/projects/fcs/winrun',
    },
    'wuk03au.vsp.sas.com': {
        'HOST': 'wuk03au.vsp.sas.com',
        'HOST_SHORT': 'wuk03au',
        'TLA': 'WUK',
        'TLA_LOWER_CASE': 'wuk',
        'ENV': 'DEV',
        'DB_SERVICE': 'wukdev01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'wukdev01',
        'MARKET_NAME': 'UK',
        'VA_SERVER': 'wuk04au.vsp.sas.com',
        'RUN_USER': 'wukrun',
        'RUN_PATH': '/wuk/projects/fcs/wukrun',
    },
    'win01au.vsp.sas.com': {
        'HOST': 'win01au.vsp.sas.com',
        'HOST_SHORT': 'win01au',
        'TLA': 'WIN',
        'TLA_LOWER_CASE': 'win',
        'ENV': 'PROD',
        'DB_SERVICE': 'winprd01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'winprd01',
        'MARKET_NAME': 'China',
        'VA_SERVER': 'win02au.vsp.sas.com',
        'RUN_USER': 'winrun',
        'RUN_PATH': '/win/projects/fcs/winrun',
    },
    'wbr05au.vsp.sas.com': {
        'HOST': 'wbr05au.vsp.sas.com',
        'HOST_SHORT': 'wbr05au',
        'TLA': 'WBR',
        'TLA_LOWER_CASE': 'wbr',
        'ENV': 'QA',
        'DB_SERVICE': 'wbrqa01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'wbrqa01',
        'MARKET_NAME': 'Argentina',
        'VA_SERVER': 'wbr06au.vsp.sas.com',
        'RUN_USER': 'wbrrun',
        'RUN_PATH': '/wbr/projects/fcs/wbrrun',
    },
    'win03au.vsp.sas.com': {
        'HOST': 'win03au.vsp.sas.com',
        'HOST_SHORT': 'win03au',
        'TLA': 'WIN',
        'TLA_LOWER_CASE': 'win',
        'ENV': 'TEST',
        'DB_SERVICE': 'wintst01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'wintst01',
        'MARKET_NAME': 'China',
        'VA_SERVER': 'win04au.vsp.sas.com',
        'RUN_USER': 'winrun',
        'RUN_PATH': '/win/projects/fcs/winrun',
    },
    'win07au.vsp.sas.com': {
        'HOST': 'win07au.vsp.sas.com',
        'HOST_SHORT': 'win07au',
        'TLA': 'WIN',
        'TLA_LOWER_CASE': 'win',
        'ENV': 'QA',
        'DB_SERVICE': 'winqa01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'winqa01',
        'MARKET_NAME': 'China',
        'VA_SERVER': 'win08au.vsp.sas.com',
        'RUN_USER': 'winrun',
        'RUN_PATH': '/win/projects/fcs/winrun',
    },
    'wuk05au.vsp.sas.com': {
        'HOST': 'wuk05au.vsp.sas.com',
        'HOST_SHORT': 'wuk05au',
        'TLA': 'WUK',
        'TLA_LOWER_CASE': 'wuk',
        'ENV': 'TEST',
        'DB_SERVICE': 'wuktst01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'wuktst01',
        'MARKET_NAME': 'UK',
        'VA_SERVER': 'wuk06au.vsp.sas.com',
        'RUN_USER': 'wukrun',
        'RUN_PATH': '/wuk/projects/fcs/wukrun',
    },
    'wuk07au.vsp.sas.com': {
        'HOST': 'wuk07au.vsp.sas.com',
        'HOST_SHORT': 'wuk07au',
        'TLA': 'WUK',
        'TLA_LOWER_CASE': 'wuk',
        'ENV': 'QA',
        'DB_SERVICE': 'wukqa01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'wukqa01',
        'MARKET_NAME': 'UK',
        'VA_SERVER': 'wuk08au.vsp.sas.com',
        'RUN_USER': 'wukrun',
        'RUN_PATH': '/wuk/projects/fcs/wukrun',
    },
    'wuk01au.vsp.sas.com': {
        'HOST': 'wuk01au.vsp.sas.com',
        'HOST_SHORT': 'wuk01au',
        'TLA': 'WUK',
        'TLA_LOWER_CASE': 'wuk',
        'ENV': 'PROD',
        'DB_SERVICE': 'wukprd01.vsp.sas.com',
        'DB_SERVICE_SHORT': 'wukprd01',
        'MARKET_NAME': 'UK',
        'VA_SERVER': 'wuk02au.vsp.sas.com',
        'RUN_USER': 'wukrun',
        'RUN_PATH': '/wuk/projects/fcs/wukrun',
    }
}

def print_usage():
    """ This function will print the usage of the ssodETLProcess.py file
    :return: none
    """
    print '[USAGE1] python sso_create_initial_env_tickets.py -s <server fqdn> -c <path to CSV file> -m <master JIRA ticket> -p <password to run>'
    print '[EXAMPLE] python sso_create_initial_env_tickets.py -s wbr01au.vsp.sas.com -c ./wbr_dev.csv -m \'WBR-60\' -p 023432jjsk'
    sys.exit(2)

def check_args():
    """
    This function will run inputs through some basic validations.
    :return: True upon success.
    :rtype: bool
    """
    print_debug('In check_args: checking arguments...')
    global run_password_default, server_fqdn, csv_file_path, master_jira_ticket, run_password, environment_config

    if run_password != run_password_default:
        raise Exception('Invalid password!')

    if server_fqdn not in environment_config:
        raise Exception('Invalid server environment: ' + server_fqdn)

    jira_split = master_jira_ticket.split('-')
    if len(jira_split) != 2:
        raise Exception('Invalid master JIRA ticket.  Needs to be in TLA-XXX format')

    if jira_split[0] != environment_config[server_fqdn]['TLA']:
        raise Exception('JIRA ticket TLA does not match environment: ' + jira_split[0] + ' != ' + environment_config[server_fqdn]['TLA'])

    fev = FileExistsValidator(True)
    abs_csv_path = os.path.abspath(csv_file_path)
    if not fev.validate(abs_csv_path):
        raise Exception(fev.format_errors())

    print_debug('Arguments have passed initial checks.')

    return True

def tokenize(data):
    global run_password_default, server_fqdn, csv_file_path, master_jira_ticket, run_password, environment_config, num_cols_expected_in_csv, default_assignee
    data = str(unicode(data, errors='ignore')).strip()
    for token in environment_config[server_fqdn]:
        data = data.replace('{' + token + '}', environment_config[server_fqdn][token])
    return data

def get_labels(data):
    global run_password_default, server_fqdn, csv_file_path, master_jira_ticket, run_password, environment_config, num_cols_expected_in_csv, default_assignee
    data = str(data).strip()
    default_label = environment_config[server_fqdn]['TLA'] + '_ENVIRONMENT_CONFIG, WMT_INITIAL_ENV_CONFIG'
    return default_label if data == '' else default_label + ',' + data

def create_jira_from_row(row):
    print_debug('In create_jira_from_row')
    global run_password_default, server_fqdn, csv_file_path, master_jira_ticket, run_password, environment_config, num_cols_expected_in_csv, default_assignee
    if len(row) != num_cols_expected_in_csv:
        raise Exception('Invalid number of columns. Expecting ' + str(num_cols_expected_in_csv) + ' columns and received ' + str(len(row)))

    ticket_summary = tokenize(row[0])
    ticket_description = tokenize(row[1])
    ticket_labels = tokenize(row[2])

    if ticket_summary == '':
        print_debug('ticket summary is blank and cannot be blank')
        return False

    if ticket_description == '':
        print_debug('ticket description is blank and cannot be blank')
        return False

    try:
        ticket_include_dev = int(row[3])
    except Exception as e:
        print_debug('Could not convert ticket_include_dev to an int: ' + str(e))
        ticket_include_dev = 0

    try:
        ticket_include_test = int(row[4])
    except Exception as e:
        print_debug('Could not convert ticket_include_test to an int: ' + str(e))
        ticket_include_test = 0

    try:
        ticket_include_qa = int(row[5])
    except Exception as e:
        print_debug('Could not convert ticket_include_qa to an int: ' + str(e))
        ticket_include_qa = 0

    try:
        ticket_include_prod = int(row[6])
    except Exception as e:
        print_debug('Could not convert ticket_include_prod to an int: ' + str(e))
        ticket_include_prod = 0

    if ticket_include_dev != 1 and ticket_include_test != 1 and ticket_include_qa != 1 and ticket_include_prod != 1:
        print_debug('No environments are included for this ticket - closing.')
        return False

    create_ticket = False
    if environment_config[server_fqdn]['ENV'] == 'DEV' and ticket_include_dev == 1:
        print_debug('ENV is DEV and include = 1...creating ticket')
        create_ticket = True
    elif environment_config[server_fqdn]['ENV'] == 'TEST' and ticket_include_test == 1:
        print_debug('ENV is TEST and include = 1...creating ticket')
        create_ticket = True
    elif environment_config[server_fqdn]['ENV'] == 'QA' and ticket_include_qa == 1:
        print_debug('ENV is QA and include = 1...creating ticket')
        create_ticket = True
    elif environment_config[server_fqdn]['ENV'] == 'PROD' and ticket_include_prod == 1:
        print_debug('ENV is PROD and include = 1...creating ticket')
        create_ticket = True

    if not create_ticket:
        print_debug('[NO TICKET CREATION] ' + environment_config[server_fqdn]['ENV'] + ' not in ' + str(ticket_include_dev) + '|' + str(ticket_include_test) + '|' + str(ticket_include_qa) + '|' + str(ticket_include_prod))
        return False

    row_info = Info()
    row_info.project = environment_config[server_fqdn]['TLA']
    row_info.assignee = default_assignee
    row_info.summary = ticket_summary
    row_info.priority = 'minor'
    row_info.type = 'subtask'
    row_info.labels = get_labels(ticket_labels)
    row_info.description = ticket_description
    row_info.parent = master_jira_ticket
    row_info.notify = 'No'

    jira_obj = Jira()
    jira_obj.create(row_info)

    return True

def create_tickets_from_csv():
    """
    This function will validate the CSV, rows and pass off to JIRA ticket creation
    :return: True upon success
    :rtype: bool
    """
    try:
        print_debug('In create_tickets_from_csv: reading CSV')
        row_cntr = 1
        global run_password_default, server_fqdn, csv_file_path, master_jira_ticket, run_password, environment_config, num_cols_expected_in_csv
        with open(csv_file_path, 'rb') as csvfile:
            env_config_csv = csv.reader(csvfile, delimiter=',', quotechar='"', dialect="excel")
            for row in env_config_csv:
                print '-------------------------------- [START ROW #' + str(row_cntr) + '] --------------------------------'
                print_debug('[ROW #' + str(row_cntr) + ']')
                if row_cntr == 1:
                    print_debug('Skipping header row...')
                    row_cntr += 1
                    continue
                print_debug(row)
                create_jira_from_row(row)
                print '-------------------------------- [END ROW #' + str(row_cntr) + '] ----------------------------------'
                row_cntr += 1
        return True
    except Exception as e:
        raise Exception('Caught exception in create_tickets_from_csv: ' + str(e))

def print_debug(msg):
    print 'DEBUG: ' + str(msg).strip()

def main(argv):
    """ This is the main run process for SSOD automations.
    :param argv: array
    :return: none
    """
    global run_password_default, server_fqdn, csv_file_path, master_jira_ticket, run_password, environment_config

    # try to determine the input arguments.
    try:
        opts, args = getopt.getopt(argv, "hs:c:m:p:")
        for opt, arg in opts:
            if opt == '-h':
                print_usage()
            elif opt == "-s":
                server_fqdn = str(arg).strip()
            elif opt == "-c":
                csv_file_path = str(arg).strip()
            elif opt == "-m":
                master_jira_ticket = str(arg).strip()
            elif opt == "-p":
                run_password = str(arg).strip()

        if not server_fqdn or not csv_file_path or not master_jira_ticket or not run_password:
            print_usage()

        print_debug('All options specified.')
        check_args()
        create_tickets_from_csv()
    except getopt.GetoptError as e:
        # throw error on any get options error.
        print 'Invalid arguments: ' + str(e)
        print_usage()
    except Exception as e:
        print '--------------------------------------------------'
        print str(e)
        print '--------------------------------------------------'
        traceback.print_exc()
        sys.exit(2)

# this is how we invoke the main method to start everything off and we pass in argv from sys.
if __name__ == "__main__":
    main(sys.argv[1:])