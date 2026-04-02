#!/usr/bin/env /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python
import os
import sys
import argparse
from pyzabbix import ZabbixAPI

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Thycotic import AMSSecretServer
from Toolkit.Config import AMSConfig
from Toolkit.Lib.Defaults import AMSDefaults


def stderr_print(text):
    sys.stderr.write(text)
    sys.stderr.write(os.linesep)


def get_proxy():
    arg_parser = argparse.ArgumentParser(description='This script finds the zabbix proxy for the specified host')
    arg_parser.add_argument('-u', '--url', type=str, required=False, help='Zabbix URL')
    arg_parser.add_argument('-w', '--user', type=str, required=False, help='Zabbix username')
    arg_parser.add_argument('-p', '--password', type=str, required=False, help='Zabbix password')
    arg_parser.add_argument('-o', '--hostname', type=str, required=True, help='hostname')
    args = arg_parser.parse_args()

    ams_defaults = AMSDefaults()
    config = AMSConfig()

    user = args.user
    password = args.password

    if user is None or password is None:
        try:
            secret_server = AMSSecretServer(username=config.decrypt(ams_defaults.thycotic_func_username),
                                            password=config.decrypt(ams_defaults.thycotic_func_password), domain="")
            user = secret_server.get_secret_field(secret_id=ams_defaults.default_zabbix_secret_id, slug='username')
            password = secret_server.get_secret_field(secret_id=ams_defaults.default_zabbix_secret_id, slug='password')
        except Exception as e:
            stderr_print('Default config file was not found as expected.')

    try:
        if args.url:
            url = args.url
        else:
            url = ams_defaults.zabbix_url
        zapi = ZabbixAPI(url=url, user=user, password=password)

        proxy_mapping = {proxy['proxy_hostid']: proxy['host'] for proxy in zapi.host.get(groupids='609')}
        host_info=zapi.host.get(filter={'host': args.hostname})
        if len(host_info):
            proxy_hostid=host_info[0]['proxy_hostid']
            if proxy_hostid in proxy_mapping:
                return proxy_mapping[proxy_hostid]
            else:
                stderr_print('Hostname {} found in zabbix as hostid={} but no proxy_mapping was found'.format(args.hostname, proxy_hostid))

        else:
            stderr_print('No hostname {} found in zabbix'.format(args.hostname))

    except Exception as e:
        stderr_print('Problem with determining proxy for hostname={}\n{}'.format(args.hostname, str(e)))
        exit(1)

    stderr_print('Defaulting to default zabbix proxy={}'.format(ams_defaults.zabbix_proxy))
    return ams_defaults.zabbix_proxy


print(get_proxy())
