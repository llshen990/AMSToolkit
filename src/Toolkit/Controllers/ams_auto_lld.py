import os
import sys
import argparse

from pyzabbix import ZabbixAPI, ZabbixSender, ZabbixMetric, ZabbixResponse

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Thycotic import AMSSecretServer
from Toolkit.Config import AMSConfig
from Toolkit.Lib.Defaults import AMSDefaults


def main():
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    ams_logger.set_debug(True)
    defaults = AMSDefaults()

    arg_parser = argparse.ArgumentParser(description='This controller reads a list of hosts from a file, applies our '
                                                     'templates, and adds the hosts to our host group. It is not '
                                                     'intended to be run manually but via automation.')
    arg_parser.add_argument('-f', '--file', type=str, required=True, help='File to read hosts from.')
    arg_parser.add_argument('-u', '--url', type=str, required=False, default=defaults.zabbix_url)
    arg_parser.add_argument('-g', '--hostgroup', type=str, required=False, default='AMS Batch Monitored Hosts')
    arg_parser.add_argument('-t', '--template', required=False, nargs='*', default=['AMS Batch Monitoring LLD - GHUSPS',
                                                                                    'AMS Web Scenario LLD - GHUSPS'])
    arg_parser.add_argument('-w', '--user', type=str, required=False, help='Zabbix username')
    arg_parser.add_argument('-p', '--password', type=str, required=False, help='Zabbix password')
    args = arg_parser.parse_args()

    config = AMSConfig()
    ams_defaults = AMSDefaults()

    user = args.user
    password = args.password

    if user is None or password is None:
        try:
            secret_server = AMSSecretServer(username=config.decrypt(ams_defaults.thycotic_func_username),
                                            password=config.decrypt(ams_defaults.thycotic_func_password), domain="")
            secret = secret_server.get_amspassword_secret(ams_defaults.default_zabbix_secret_id)
            user = secret.username
            password = secret.password
        except Exception as e:
            ams_logger.warning('Default config file was not found as expected.')

    try:
        with open(args.file, 'r') as host_file:
            hosts = [host.strip() for host in host_file.readlines()]
            ams_logger.debug('The specified file {} contained these hostnames {}'.format(args.file, hosts))
    except Exception as e:
        ams_logger.error('The provided hosts file {} appears to be invalid.\n{}'.format(args.file, sanitize(user, password, e)))
        exit(1)

    try:
        zapi = ZabbixAPI(url=args.url, user=user, password=password)
    except Exception as e:
        ams_logger.error('Error connection to zabbix instance {}\n{}'.format(args.url, sanitize(user, password, e)))
        exit(1)

    group_id = zapi.hostgroup.get(filter={'name': args.hostgroup})[0]['groupid']
    if not group_id:
        ams_logger.error('Hostgroup "{}" was not found'.format(args.hostgroup))
        exit(1)

    zabbix_hosts = zapi.host.get(filter={'host': hosts})
    hostids = [host['hostid'] for host in zabbix_hosts]
    ams_logger.debug('Attempting to add hostids {} to groupid "{}".'.format(hostids, group_id))
    group_result = zapi.hostgroup.massadd(groups=group_id, hosts=hostids)
    if not group_result:
        ams_logger.error('Hosts were not successfully added to hostgroup {}'.format(args.hostgroup))

    ams_logger.debug('Querying templateids for template(s) {}'.format(args.template))
    templateids = [{'templateid': template['templateid']} for template in zapi.template.get(filter={'name': args.template})]
    template_result = zapi.template.massadd(templates=templateids, hosts=hostids)
    if not template_result:
        ams_logger.error('Templates {} were not successfully applied to hosts {}'.format(args.template, hosts))
        exit(1)


def sanitize(username, password, e_dirty):
    nopassword_e = str(e_dirty)
    if password is not None:
        nopassword_e = nopassword_e.replace(password, 'REDACTED')
    if username is not None:
        nopassword_e = nopassword_e.replace(username, 'REDACTED')
    return nopassword_e


if __name__ == "__main__":
    main()
