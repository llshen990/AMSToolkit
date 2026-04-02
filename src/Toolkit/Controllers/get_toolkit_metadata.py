#!/usr/bin/env /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python
import json
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


def get_toolkit_metadata():
    arg_parser = argparse.ArgumentParser(description='This script finds the get_toolkit_metadata for the specified host')
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
        zapi = ZabbixAPI(url=ams_defaults.zabbix_url, user=user, password=password)

        host_info = zapi.host.get(filter={'host': args.hostname})
        if len(host_info):
            host_list = [host_info[0]['hostid']]
            host_inventory = zapi.host.get(hostids=host_list, selectHosts=['extend'], selectInventory=['tag', 'asset_tag', 'site_notes', 'software'])
            if len(host_inventory):
                # fetch the inventory for the host and create a cool json blob
                data = {'tla': host_inventory[0]['inventory']['tag'], 'datacenter': host_inventory[0]['inventory']['site_notes'], 'hostname': args.hostname, 'appservice': host_inventory[0]['inventory']['asset_tag'], 'software': host_inventory[0]['inventory']['software']}

                # find all the zabbix proxies
                try:
                    proxy_mapping = {proxy['proxy_hostid']: proxy['host'] for proxy in zapi.host.get(groupids='609')}
                    proxy_hostid = host_info[0]['proxy_hostid']
                    if proxy_hostid in proxy_mapping:
                        data['zabbix_proxy'] = proxy_mapping[proxy_hostid]
                    else:
                        data['zabbix_proxy'] = ams_defaults.zabbix_proxy
                except Exception as e:
                    stderr_print('Problem with determining proxy for hostname={}\n{}'.format(args.hostname, str(e)))

                try:
                    result = zapi.template.get(filter={'host': ams_defaults.zabbix_template_name}, selectHosts=['extend'])
                    template_id = result[0]['templateid']
                    items = zapi.item.get(hostids=host_list, output='extend', templateids=template_id + '', search={'key_': 'vfs.file.contents[/sso/sfw/ghusps-toolkit/ams-toolkit/version]'})
                    if len(items):
                        data['toolkit_version'] = items[0]['lastvalue']
                    else:
                        data['toolkit_version'] = ''

                except Exception as e:
                    stderr_print('Problem with determining toolkit version for hostname={}\n{}'.format(args.hostname, str(e)))

                return json.dumps(data, indent=2)
            else:
                stderr_print('Hostname {} found in zabbix as hostid={} but no inventory was found'.format(args.hostname, host_info))

        else:
            stderr_print('No hostname {} found in zabbix'.format(args.hostname))

    except Exception as e:
        stderr_print('Problem with determining zabbix inventory for hostname={}\n{}'.format(args.hostname, str(e)))
        exit(1)

print(get_toolkit_metadata())
