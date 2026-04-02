import sys
import os
import argparse
import json
import readline
import getpass

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Lib import AMSLogger
from Toolkit.Lib.Defaults import AMSDefaults


def _get_credentials():
    readline.set_startup_hook(lambda: readline.insert_text(current_user))
    user = raw_input('Enter VSP username: ')
    readline.set_startup_hook()
    passwd = getpass.getpass('Enter VSP password: ')
    return user, passwd


def add_retail_items(source_host, external_host, solution_type):
    template = 'AMS Health Check LLD - GHUSPS'
    if ams_zabbix.is_template_applied(template, source_host):
        # remove template
        ams_zabbix.remove_template_from_host(template, source_host)
        ams_zabbix.apply_template_to_host(template, source_host)
    try:
        ams_zabbix.add_item_to_host(hostname=source_host, key='healthCheck.MI.result', name="Health Check Result", value_type=3, application='MI Health Check')
    except:
        print 'Item already exists for Health Check Result'
    try:
        ams_zabbix.add_item_to_host(hostname=source_host, key='healthCheck.MI.message', name="Health Check Message", value_type=4, application='MI Health Check')
    except:
        print 'Item already exists for Health Check Message'

    try:
        ams_zabbix.add_calc_item_to_host(hostname=external_host, key=source_host+'_healthCheck.MI.result', formula='last("' + source_host + ':healthCheck.MI.result")', name="MI Health Check Result", value_type=4, application='Synthetic Transaction')
    except Exception as e:
        print 'Calculated item already exists for Health Check Result'


def add_ahc_items(source_host, external_host, solution_type):
    try:
        ams_zabbix.add_calc_item_to_host(hostname=external_host, key=source_host+'_healthCheck.' + solution_type + '.result', formula='last("' + source_host + ':healthCheck.' + solution_type + '.result")', name=solution_type + " Check Result", value_type=4, application='Synthetic Transaction')
    except Exception as e:
        print 'Calculated item already exists for {} Check Result'.format(solution_type)


def _add_ahc_triggers(source_host, external_host, solution_type):
    key_name = source_host + '_healthCheck.' + solution_type + '.result'
    trigger_name = 'Automated Health Check (' + solution_type + ')'
    trigger_condition = '{'+external_host+':' + key_name + '.last()}=0 and {'+external_host+':' + key_name + '.prev()}=0'

    ams_logger.info('Creating trigger with condition='+trigger_condition)

    try:
        trigger_res = ams_zabbix.add_trigger_to_host(trigger_name, trigger_condition, severity=4)
        ams_logger.debug(json.dumps(trigger_res, indent=2))
    except Exception as e:
        ams_logger.critical('Failed to add ' + trigger_name + 'Check: %s' % str(e))
        return False
    return True


def _add_retail_trigger(source_host, external_host, solution_type):
    try:
        ams_logger.debug('Adding MI Health Check Trigger...')
        if solution_type in ['SPO']:
            # this check only includes the midtier
            cwb_condition = ''
        else:
            # this check includes the midtier and the CWB
            cwb_condition = ' or ({' + external_host + ':' + source_host + '_healthCheck.MI.result.last()}=1 and {' + source_host + ':SAS.port.expected_state[{$MI_CWB_PORT}].last()}=1)'

        mi_condition = '(({' + external_host + ':' + source_host + '_healthCheck.MI.result.last()}=0 and {' + source_host + ':SAS.port.expected_state[{$MI_UI_PORT}].last()}=1) ' + cwb_condition
        nodata_condition = ' or ({' + external_host + ':' + source_host + '_healthCheck.MI.result.nodata(1800)}=1))'

        trigger_condition = mi_condition + nodata_condition

        ams_logger.debug(trigger_condition)
        trigger_res = ams_zabbix.add_trigger_to_host('MI Health Check', trigger_condition, severity=4)
        ams_logger.debug(json.dumps(trigger_res, indent=2))
    except Exception as e:
        ams_logger.error('Failed to add MI Health Check: {}'.format(str(e)))
        return False

    return True


def do_verification_add(hostname):
    return ams_zabbix.add_host_to_host_group('STP Verified', hostname)


if __name__ == "__main__":
    # noinspection PyTypeChecker
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--source_host", nargs='?', help="Fully qualified host where the health check exists", required=True)
    arg_parser.add_argument("--external_host", nargs='?', help="Fully qualified external (<tla><env>.sas.ondemand.com) host to add Triggers To", required=True)
    arg_parser.add_argument("--solution_type", nargs='?', choices=['SPO', 'MDO_RPP_RPO', 'SS', 'LSAF', 'AHC', 'VA', 'SFF'], help="SAS Solution Type", required=True)

    args = arg_parser.parse_args(sys.argv[1:])
    if not args.solution_type:
        print '{}: error: argument --solution_type is required'.format(os.path.basename(__file__))
        exit(1)

    source_host = args.source_host.strip()
    external_host = args.external_host.strip()
    solution_type = args.solution_type.strip()

    ams_logger = AMSLogger()
    ams_logger.set_debug(True)

    current_user = getpass.getuser()

    if AMSDefaults().is_dev_host():
        username, password = '', ''
    else:
        username, password = _get_credentials()

    ams_zabbix = AMSZabbix(ams_logger, username=username, password=password)

    success = False

    # Verify that source_host and external_host exist before proceeding
    if not ams_zabbix.is_host_exist(source_host):
        print 'Host {} does not exist in zabbix'.format(source_host)
        exit(2)

    if not ams_zabbix.is_host_exist(external_host):
        print 'Host {} does not exist in zabbix'.format(external_host)
        exit(3)

    if solution_type in ["SPO", "MDO_RPP_RPO"]:
        add_retail_items(source_host, external_host, solution_type)
        success = _add_retail_trigger(source_host, external_host, solution_type)
    else:
        add_ahc_items(source_host, external_host, solution_type)
        success = _add_ahc_triggers(source_host, external_host, solution_type)

    if success:
        do_verification_add(source_host)
        do_verification_add(external_host)
        exit(0)
    else:
        exit(1)