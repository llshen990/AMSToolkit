import argparse
import sys
import traceback
import readline
import getpass
from six.moves import input
import os
import json

from pyzabbix import ZabbixAPI

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Exceptions import AMSExceptionNoEventNotification, AMSValidationException
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Thycotic import AMSSecretServer
from Toolkit.Config import AMSConfig


def _get_credentials():
    readline.set_startup_hook(lambda: readline.insert_text(current_user))
    user = input('Enter Your Zabbix Username (VSP): ')
    readline.set_startup_hook()
    passwd = getpass.getpass('Enter Your Zabbix Password (VSP): ')
    return user, passwd

def get_host_by_hostid(host_id, host_names):
    for i in host_names:
        if i['hostid'] == host_id:
            return i['host']
    return '(id = {})'.format(host_id)

if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    current_user = AMSDefaults().current_user
    ams_defaults = AMSDefaults()

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--zabbix_url", nargs='?', type=str, help="Zabbix URL", required=False, default=ams_defaults.zabbix_url)

    args = arg_parser.parse_args()
    ams_logger.set_debug(False)

    # if we don't pass in the host, we'll grab it from the config and it will be assumed to be the current host.
    ams_logger.debug('host={}'.format(ams_defaults.my_hostname))

    try:
        # username, password = _get_credentials()
        pass
    except Exception as e:
        raise AMSValidationException('Failed to capture user credentials.')

    try:
        ams_config = AMSConfig()
        secret_server = AMSSecretServer(username=ams_config.decrypt(ams_defaults.thycotic_func_username), password=ams_config.decrypt(ams_defaults.thycotic_func_password), domain="")
        secret = secret_server.get_amspassword_secret(ams_defaults.default_zabbix_secret_id)
        zapi = ZabbixAPI(url=ams_defaults.zabbix_url, user=secret.username, password=secret.password)
        ams_logger.info('Getting all hosts with template {} '.format(ams_defaults.zabbix_template_name))

        result = zapi.template.get(filter={'host': ams_defaults.zabbix_template_name}, selectHosts=['extend'])
        hosts = result[0]['hosts']
        template_id = result[0]['templateid']
        ams_logger.info('Found {} hosts'.format(len(hosts)))

        host_list = []
        for i in hosts:
            host_list.append(i['hostid'])

        ams_logger.info('Retrieving host names for hosts...')
        host_names = zapi.host.get(hostids=host_list, selectHosts=['extend'])

        ams_logger.info('Retrieving version information for hosts...')
        items = zapi.item.get(hostids=host_list, output='extend', templateids=template_id + '', search={'key_': 'vfs.file.contents[/sso/sfw/ghusps-toolkit/ams-toolkit/version]'})

        ams_logger.info('Found {} items'.format(len(hosts)))

        version_dict = {}
        for item in items:
            host = get_host_by_hostid(item['hostid'], host_names)
            value = item['lastvalue']
            if len(value) == 0:
                value = 'NONE'
            version_dict[host] = value

        print(json.dumps(version_dict))

    except KeyboardInterrupt:
        ams_logger.error('{}User killed process with ctrl+c...'.format(os.linesep))
    except AMSExceptionNoEventNotification as e:
        ams_logger.error("{}Process exited with a AMSExceptionNoEventNotification exception: {}{}".format(os.linesep, AMSZabbix.sanitize_error(e), os.linesep))
    except Exception as e:
        ams_logger.error("Traceback: " + traceback.format_exc())
        ams_logger.error("Caught an exception running {}: {}".format(__file__, e))
