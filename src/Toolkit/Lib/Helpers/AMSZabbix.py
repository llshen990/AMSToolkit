import os
import sys
import time
from datetime import datetime
from pyzabbix import ZabbixAPI, ZabbixSender, ZabbixMetric, ZabbixResponse

from Toolkit.Exceptions import AMSZabbixException
from Toolkit.Lib.Defaults import AMSDefaults

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)


class AMSZabbix(object):
    def __init__(self, logger, config=None, use_zabbix_config=False, hostname=None, username=None, password=None):
        """
        :param logger: The Logger instance
        :type logger: AMSLogger
        :param use_zabbix_config: Determines whether or not the zabbix_sender uses the default zabbix config file.
        :type use_zabbix_config: bool
        :param config: The Config instance
        :type config: AMSConfig
        :param hostname: Optional Zabbix sender hostname. This is used if the sending host is collecting and sending metrics for another host.
        :type hostname: str
        """
        self.logger = logger
        self.config = config
        self.retry_limit = 3
        self.retry_timeout = 30
        self.socket_timeout = 60
        self.quiet_mode = False
        self.defaults = AMSDefaults()

        # determine hostname
        if hostname is not None:
            self.my_hostname = hostname
        elif self.config is not None:
            self.my_hostname = self.config.my_hostname
        else:
            self.my_hostname = self.defaults.my_hostname

        if use_zabbix_config:
            self.use_zabbix_config = True

        if AMSDefaults.is_dev_host(self.my_hostname):
            self.use_zabbix_config = True
            # This is the out of the box zabbix installed url and credentials
            self.url = 'http://localhost/zabbix/'
            self.username = 'Admin'
            self.password = 'zabbix'
            self.retry_limit = 0
        else:
            self.use_zabbix_config = False
            self.zabbix_proxy = self.defaults.zabbix_proxy
            self.url = self.defaults.zabbix_url
            self.username = username
            self.password = password

            # If a zabbix proxy was configured in the config, then use it
            if config and config.zabbix_proxy:
                self.zabbix_proxy = config.zabbix_proxy

            # If a zabbix url was configured in the config, then use it
            if config and config.zabbix_url:
                self.url = config.zabbix_url

            # If zabbix retry_timeout was configured in the config, then use it
            if config and config.zabbix_retry_timeout:
                self.retry_timeout = config.zabbix_retry_timeout

            # If zabbix retry_limit was configured in the config, then use it
            if config and config.zabbix_retry_limit:
                self.retry_limit = config.zabbix_retry_limit

            # If zabbix socket_timeout was configured in the config, then use it
            if config and config.zabbix_socket_timeout:
                self.socket_timeout = config.zabbix_socket_timeout

    # noinspection PyMethodMayBeStatic
    def __get_secret_key(self):
        return "{0: <32}".format('2ldij3204%$#^ESAvljuwA0xlkjsd0').encode("utf-8")

    def call_zabbix_sender(self, zabbix_key, zabbix_value, force_send=False):
        """
        This method uses the 'zabbix_sender' executable to send monitoring data to the Zabbix server.
        :param zabbix_key: The Zabbix item key.
        :type zabbix_key: str
        :param zabbix_value: The Zabbix item value.
        :type zabbix_value: str
        :param force_send: Whether or not to force sending the message if previous sends have failed
        :type force_send: bool
        :return: True upon success or return false upon failure
        :rtype: bool
        """

        if not zabbix_key:
            self.logger.error("call_zabbix_sender requires zabbix_key")
            return False

        if not zabbix_value:
            self.logger.error("call_zabbix_sender requires zabbix_value")
            return False

        zabbix_key = str(zabbix_key).strip()
        zabbix_value = str(zabbix_value).strip()
        if len(zabbix_value) > 30000:
            zabbix_value = zabbix_value[:30000] + '\n-----THIS MESSAGE HAS BEEN TRUNCATED-----'

        if self.use_zabbix_config:
            self.logger.info("Updating Zabbix - Config: {0}, Host: {1}, Key: {2}, Value: {3}".format(self.defaults.zabbix_config_file, self.my_hostname, zabbix_key, zabbix_value))
            zsend = ZabbixSender(use_config=self.defaults.zabbix_config_file)
        else:
            self.logger.info("Updating Zabbix - Proxy: {0}, Host: {1}, Key: {2}, Value: {3}".format(self.zabbix_proxy, self.my_hostname, zabbix_key, zabbix_value))
            zsend = ZabbixSender(zabbix_server=self.zabbix_proxy)
        self.logger.debug("retry_limit: {0}, retry_timeout: {1}".format(self.retry_limit, self.retry_timeout))
        self.logger.debug("Zabbix sender={0}".format(zsend))

        if force_send:
            self.quiet_mode = False

        self.logger.debug("Zabbix: retry_limit={}, retry_timeout={}, socket_timeout={}".format(self.retry_limit, self.retry_timeout, self.socket_timeout))

        if self.quiet_mode:
            self.logger.warning("******* Zabbix sending is suppressed because of connectivity issues *******")
        else:
            num_retries = 0
            while True:
                import socket
                default = socket.getdefaulttimeout()
                try:
                    socket.setdefaulttimeout(self.socket_timeout)
                    result = zsend.send([ZabbixMetric(self.my_hostname, zabbix_key, zabbix_value)])
                except Exception as e:
                    self.logger.error("Caught exception while trying to update Zabbix: %s" % self.sanitize_error(e))
                    result = ZabbixResponse()
                    result._failed += int(1)
                    result._total += int(1)
                    result._chunk += 1
                finally:
                    socket.setdefaulttimeout(default)

                if result.failed > 0:
                    self.logger.warning("There was a problem updating Zabbix.")
                    self.logger.warning("ZabbixResult: {0}".format(result))
                    self.logger.warning("Zabbix sender key: {0} value: {1}".format(zabbix_key, zabbix_value))

                    if num_retries < self.retry_limit:
                        self.logger.warning("Failed to update zabbix.  Going to retry " + str(self.retry_limit - num_retries) + " more times.")
                        num_retries += 1
                        self.logger.info("Sleeping " + str(self.retry_timeout) + " seconds before trying to resend to Zabbix...")
                        time.sleep(self.retry_timeout)
                    else:
                        # if we've tried too many times or num_retries is out of range
                        break
                else:
                    # exit the while look if result was 0 (success)
                    break

            if result.failed:
                self.logger.error("There was an error while updating Zabbix hostname {} key {} with value='{}'".format(self.my_hostname, zabbix_key, zabbix_value))
                self.quiet_mode = True
                return False
            else:
                if num_retries > 0:
                    self.logger.info("Successfully updated Zabbix on the " + str(num_retries) + " attempt.")
                self.logger.debug("Successfully updated zabbix key=\'" + zabbix_key)

        return True

    def is_authenticated(self):
        """
        This method uses the Zabbix API python package to check if user/password is valid.
        :rtype: bool
        """
        self.logger.info("Checking if ZabbixAPI is valid")

        try:
            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)
        except Exception as e:
            return False

        return True

    def is_template_applied(self, template_name, hostname):
        """
        This method uses the Zabbix API python package to check if the specified template is applied to the given host and returns a boolean.
        :param template_name: The name of the specified template that must already exist.
        :type template_name: str
        :param hostname: The given hostname.
        :type hostname: str
        :return: True upon success or False if: a) template is not defined in zabbix b) host is not defined in zabbix c) other unhandled issues.
        :rtype: bool
        """
        if not template_name:
            self.logger.error("is_template_applied requires template_name")
            return False

        if not hostname:
            self.logger.error("is_template_applied requires hostname")
            return False

        self.logger.info("Checking if template {} is applied on hostname {}".format(template_name, hostname))

        try:
            try:
                zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)
            except Exception as e:
                e_str = self.sanitize_error(e)
                self.logger.error("Error: {}".format(e_str))
                self.logger.error("Due to an invalid username or password, the call has failed.")
                raise AMSZabbixException(e_str)

            result = zapi.host.get(filter={'host': hostname}, selectParentTemplates=['name'])

            result = result[0] if len(result) > 0 else {}
            self.logger.debug("Got result {} from host.get on hostname {}".format(result, hostname))

            if 'parentTemplates' in result.keys():
                templates = result['parentTemplates']
                self.logger.debug("Found parentTemplates {} on hostname {}".format(templates, hostname))
                for template in templates:
                    if 'name' in template and template['name'] == template_name:
                        self.logger.info("Successfully found template {} on hostname {}".format(template_name, hostname))
                        return True

            self.logger.info("No template {} found on hostname {}".format(template_name, hostname))
            return False
        except Exception as e:
            self.logger.error("Error: {}".format(self.sanitize_error(e)))
            return False

    def apply_template_to_host(self, template_name, hostname, clear_cache=True):
        """
        This uses the Zabbix API python package to add a template to a given host.
        :param template_name: The name of the specified template that must already exist.
        :type template_name: str
        :param hostname: The given hostname.
        :type hostname: str
        :return: True upon success or False upon failure
        :rtype: bool
        """
        if not template_name:
            self.logger.error("apply_template_to_host requires template_name")
            return False

        if not hostname:
            self.logger.error("apply_template_to_host requires hostname")
            return False

        self.logger.info("Applying template {} to hostname {}".format(template_name, hostname))

        try:
            # get the templateid for template_name
            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)
            itemlist = zapi.template.get(output='extend', filter={"name": template_name})

            self.logger.debug("Got itemlist {} on template {}".format(itemlist, template_name))

            if len(itemlist) is 1:
                template_id = int(itemlist[0]['templateid'])
            else:
                self.logger.error("Template {} does not exist".format(template_name))
                self.logger.error('Failure applying template "{}" to hostname "{}" (template does not exist)'.format(template_name, hostname))
                return False

            self.logger.debug("Template id is {} for template {}".format(template_id, template_name))

            # find the hostid for the hostname
            host = zapi.host.get(filter={'host': hostname})

            if len(host) > 0:
                host_id = host[0]['hostid']
                self.logger.debug("Got host_id {} from host.get on hostname {}".format(host_id, hostname))
            else:
                self.logger.error("Failure finding host_id for hostname {}".format(hostname))
                self.logger.error('Failure applying template "{}" to hostname "{}"'.format(template_name, hostname))
                return False

            # add templateid to existing host using the ids
            result = zapi.template.massadd(templates=template_id, hosts=host_id)
            self.logger.debug("Got result {} from template.massadd on hostname {}".format(result, host_id))

            # success means the templateid is returned
            if len(result) is 1 and 'templateids' in result and template_id in result['templateids']:
                self.logger.info("Successfully applied template {} to hostname {}".format(template_name, hostname))
                return True
            else:
                self.logger.error("Failure applying template {} on hostname {}".format(template_name, hostname))
                return False
        except Exception as e:
            self.logger.error("Error: {}".format(self.sanitize_error(e)))
            return False
        finally:
            if clear_cache and not self.clear_proxy_config_cache():
                self.logger.info("Failed to clear proxy config cache.")

    def remove_template_from_host(self, template_name, hostname):
        """
        This uses the Zabbix API python package to add a template to a given host.
        :param template_name: The name of the specified template that must already exist.
        :type template_name: str
        :param hostname: The given hostname.
        :type hostname: str
        :return: True upon success or False upon failure
        :rtype: bool
        """
        if not template_name:
            self.logger.error("remove_template_from_host requires template_name")
            return False

        if not hostname:
            self.logger.error("remove_template_from_host requires hostname")
            return False

        self.logger.info("Removing template {} from hostname {}".format(template_name, hostname))

        try:
            # get the templateid for template_name
            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)
            itemlist = zapi.template.get(output='extend', filter={"name": template_name})

            self.logger.debug("Got itemlist {} on template {}".format(itemlist, template_name))

            if len(itemlist) is 1:
                template_id = int(itemlist[0]['templateid'])
            else:
                self.logger.error("Template {} does not exist".format(template_name))
                self.logger.error('Failure removing template "{}" from hostname "{}" (template does not exist)'.format(template_name, hostname))
                return False

            self.logger.debug("Template id is {} for template {}".format(template_id, template_name))

            # find the hostid for the hostname
            host = zapi.host.get(filter={'host': hostname})

            if len(host) > 0:
                host_id = host[0]['hostid']
                self.logger.debug("Got host_id {} from host.get on hostname {}".format(host_id, hostname))
            else:
                self.logger.error("Failure finding host_id for hostname {}".format(hostname))
                self.logger.error('Failure applying template "{}" to hostname "{}"'.format(template_name, hostname))
                return False

            # remove templateid from existing host using the ids
            result = zapi.host.massremove(templateids_clear=template_id, hostids=[host_id])
            self.logger.debug("Got result {} from host.massremove on hostname {}".format(result, host_id))

            # success means the hostids is returned
            if len(result) is 1 and 'hostids' in result and host_id in result['hostids']:
                self.logger.info("Successfully removed template {} from hostname {}".format(template_name, hostname))
                return True
            else:
                self.logger.error("Failure removed template {} from hostname {}".format(template_name, hostname))
                return False
        except Exception as e:
            self.logger.error("Error: {}".format(self.sanitize_error(e)))
            return False
        finally:
            if not self.clear_proxy_config_cache():
                self.logger.info("Failed to clear proxy config cache.")

    def is_host_exist(self, hostname):
        if not hostname:
            self.logger.error('is_host_exist requires hostname')
            return False

        host = self._get_host(hostname)
        host_id = None
        if host is not None:
            host_id = host['hostid']

        if host_id is None:
            self.logger.error('Could not find hostid in host result: %s' % str(host))
            return False
        else:
            return True

    def is_host_in_host_group(self, host_group_name, hostname):
        """
        This method uses the Zabbix API python package to check if the host is already a part of the given host group and returns a boolean.
        :param host_group_name: The name of the specified host group that must already exist.
        :type host_group_name: str
        :param hostname: The given hostname.
        :type hostname: str
        :return: True upon success or False if: a) host group is not defined in zabbix b) host is not defined in zabbix c) other unhandled issues.
        :rtype: bool
        """
        if not host_group_name:
            self.logger.error('is_host_in_host_group requires host_group_name')
            return False

        if not hostname:
            self.logger.error('is_host_in_host_group requires hostname')
            return False

        self.logger.info("Checking if hostname {} is part of hostgroup {}".format(hostname, host_group_name))

        try:
            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)
            result = zapi.hostgroup.get(filter={'name': host_group_name})

            self.logger.debug("Got result {} from hostgroup.get on hostgroup name {}".format(result, host_group_name))

            if len(result) != 1:
                self.logger.error('Host group "{}" does not exist'.format(host_group_name))
                return False

            host_group_id = result[0]['groupid']

            self.logger.debug("Hostgroup id is {} for hostgroup {}".format(host_group_id, host_group_name))

            result = zapi.host.get(filter={'host': hostname}, groupids=host_group_id)
            result = result[0] if len(result) > 0 else None

            self.logger.debug("Got result {} from host.get on hostgroup {} filtered on hostname {}".format(result, host_group_name, hostname))

            if result is not None and hostname in result['name']:
                self.logger.info("Successfully found hostname {} on hostgroup {}".format(hostname, host_group_name))
                return True
            else:
                self.logger.info("No hostname {} found on hostgroup {}".format(hostname, host_group_name))
                return False
        except Exception as e:
            self.logger.error("Error: {}".format(self.sanitize_error(e)))
            return False

    def add_host_to_host_group(self, host_group_name, hostname):
        """
        This uses the Zabbix API python package to add a host to a host group.
        :param host_group_name: The name of the specified host group that must already exist.
        :type host_group_name: str
        :param hostname: The given hostname.
        :type hostname: str
        :return: True upon success or False upon failure
        :rtype: bool
        """
        if not host_group_name:
            self.logger.error('add_host_to_host_group requires host_group_name')
            return False

        if not hostname:
            self.logger.error('add_host_to_host_group requires hostname')
            return False

        self.logger.info("Adding hostname {} to hostgroup {}".format(hostname, host_group_name))

        try:
            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)
            result = zapi.hostgroup.get(filter={'name': host_group_name})

            self.logger.debug("Got result {} from hostgroup.get on hostgroup name {}".format(result, host_group_name))

            if len(result) != 1:
                self.logger.error('Hostgroup "{}" does not exist'.format(host_group_name))
                return False

            host_group_id = None

            if 'groupid' in result[0].keys():
                host_group_id = result[0]['groupid']

            if host_group_id is None:
                self.logger.error('Could not find groupid in response from zabbix: %s' % result[0])
                return False

            self.logger.debug("Hostgroup id is {} for hostgroup {}".format(host_group_id, host_group_name))

            # find the hostid for the hostname
            host = self._get_host(hostname)
            host_id = None
            if host is not None:
                host_id = host['hostid']

            if host_id is None:
                self.logger.error('Could not find hostid in host result: %s' % str(host))
                return False

            if host_id is not None:
                self.logger.debug("Got host_id {} from host.get on hostname {}".format(host_id, hostname))
            else:
                self.logger.error('Cannot find host_id for hostname'.format(hostname))
                return False

            # add templateid to existing host using the ids
            result = zapi.hostgroup.massadd(groups=host_group_id, hosts=host_id)
            self.logger.debug("Got result {} from hostgroup.massadd on hostgroup {} and hostname {}".format(result, host_group_name, hostname))

            if len(result) == 1:
                self.logger.info("Successfully added hostname {} to hostgroup {}".format(hostname, host_group_name))
                return True
            else:
                self.logger.error("Failure adding host {} to host group {}".format(hostname, host_group_name))
                return False
        except Exception as e:
            self.logger.error("Error: {}".format(self.sanitize_error(e)))
            return False
        finally:
            self.clear_proxy_config_cache()

    def clear_proxy_config_cache(self):
        """
        This uses the Zabbix API python package to call a 'zabbix script' that clears the proxy config cache.
        :return: True upon success or False upon failure
        :rtype: bool
        """
        result = None
        host_id = None
        scriptid = None
        try:
            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)

            script = self._get_script(self.defaults.zabbix_clear_proxy_config_cache_command)
            if script is not None:
                scriptid = script['scriptid']
            hostname = self.defaults.zabbix_clear_proxy_config_cache_hostname

            # find the hostid for the hostname
            host = self._get_host(hostname)
            if host is not None and 'hostid' in host.keys():
                host_id = host['hostid']

            self.logger.debug("Host id is {} for hostname {}".format(host_id, hostname))

            if host_id is not None and scriptid is not None:
                result = zapi.script.execute(hostid=host_id, scriptid=scriptid)
                self.logger.debug("Got result {} from script.execute on host_id {} and scriptid {}".format(result, host_id, scriptid))

            if len(result) > 0:
                self.logger.info("Successfully executed scriptid {} on hostname {}".format(scriptid, hostname))
                return True
            else:
                self.logger.error("Failure executing scriptid {} on hostname {}".format(scriptid, hostname))
                return False
        except Exception as e:
            self.logger.error("Error: {}".format(self.sanitize_error(e)))
            return

    def _get_script(self, command, **kwargs):
        """
        Wrapper for Zabbix python API to get the scriptid given the command string. Trust but verify, if the result
        does not match the expectation assume the script was not found.
        :param command:
        :rtype: dict
        """
        zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)

        try:
            script = zapi.script.get(filter={'command': command}, **kwargs)
            if len(script) > 0:
                script = script[0]
                if script['command'] == command:
                    return script
                else:
                    self.logger.debug('The zabbix API returned a script that does not match the one queried for: {} != {}'.format(command, script['command']))
            else:
                self.logger.debug('Command not found: {}'.format(command))
            return None
        except Exception as e:
            self.logger.error("Error: {}".format(self.sanitize_error(e)))
            return False

    def _get_host(self, hostname, **kwargs):
        """
        Wrapper for Zabbix python API to get a hostid for a given hostname. Trust but verify, if the result does not
        match the expectation assume the host was not found.
        :param hostname:
        :rtype: dict
        """
        try:
            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)
            host = zapi.host.get(filter={'host': hostname}, **kwargs)
            if isinstance(host, list) and len(host) > 0:
                host = host[0]
                if 'host' in host.keys():
                    if host['host'] == hostname:
                        return host

            return None
        except Exception as e:
            self.logger.error("Error: {}".format(self.sanitize_error(e)))
            return False

    def is_key_exist_for_host(self, key, hostname):
        """
        This uses the Zabbix API python package to check if a key exists for a given host.
        :param key: The Zabbix key that must already exist.
        :type key: str
        :param hostname: The given hostname.
        :type hostname: str
        :return: True upon success or False upon failure
        :rtype: bool
        """
        if not key:
            self.logger.error('is_key_exist_for_host requires key')
            return False

        if not hostname:
            self.logger.error('is_key_exist_for_host requires hostname')
            return False

        self.logger.info("Checking if key {} exists on hostname {}".format(key, hostname))

        try:
            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)

            result = zapi.item.get(filter={'host': hostname}, search={'key_': key}, output=['name'])
            self.logger.debug("Got result {} from item.get on hostname {} and key_ {}".format(result, hostname, key))

            if len(result) > 0:
                self.logger.info("Successfully found key {} on hostname {}".format(key, hostname))
                return True
            else:
                self.logger.error("No key {} found on hostname {}".format(key, hostname))
                return False
        except Exception as e:
            self.logger.error("Error {}".format(self.sanitize_error(e)))
            return False

    def sanitize_error(self, e_dirty):
        nopassword_e = str(e_dirty)
        if self.password is not None:
            nopassword_e = nopassword_e.replace(self.password, 'REDACTED')
        if self.username is not None:
            nopassword_e = nopassword_e.replace(self.username, 'REDACTED')
        return nopassword_e

    def add_item_to_host(self, hostname, key, name, value_type, application):
        try:
            host = self._get_host(hostname)
            host_id = None
            if host is not None:
                host_id = host['hostid']

            if host_id is None:
                self.logger.error('Could not find hostid in host result: %s' % str(host))
                return False

            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)
            app = zapi.application.get(filter={"name": application}, hostids=host_id)
            if app:
                application_id = app[0]['applicationid']
            else:
                # create the application in the host
                result = zapi.application.create(name=application, hostid=host_id)
                application_id = result['applicationids'][0]

            description = 'Created by ams-toolkit at {}'.format(datetime.now())

            result = zapi.item.create(hostid=host_id, name=name, key_=key, delay=30, type=2, value_type=value_type, applications=[application_id], description=description)
            return result

        except Exception as e:
            raise AMSZabbixException(self.sanitize_error(e))

    def add_calc_item_to_host(self, hostname, key, formula, name, value_type, application):
        try:
            host = self._get_host(hostname)
            host_id = None
            if host is not None:
                host_id = host['hostid']

            if host_id is None:
                self.logger.error('Could not find hostid in host result: %s' % str(host))
                return False

            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)
            app = zapi.application.get(filter={"name": application}, hostids=host_id)
            if app:
                application_id = app[0]['applicationid']
            else:
                # create the application in the host
                result = zapi.application.create(name=application, hostid=host_id)
                application_id = result['applicationids'][0]

            description = 'Created by ams-toolkit at {}'.format(datetime.now())

            result = zapi.item.create(hostid=host_id, name=name, key_=key, params=formula, delay=300, type=15, value_type=value_type, applications=[application_id], description=description)
            return result

        except Exception as e:
            raise AMSZabbixException(self.sanitize_error(e))

    def add_trigger_to_host(self, description, expression, severity=0):
        description = description.strip()
        expression = expression.strip()

        if not description:
            raise AMSZabbixException('description required for add_trigger_to_host')

        if not expression:
            raise AMSZabbixException('expression required for add_trigger_to_host')

        try:
            zapi = ZabbixAPI(url=self.url, user=self.username, password=self.password)

            comments = 'Created by ams-toolkit at {}'.format(datetime.now())

            result = zapi.trigger.create(description=description, expression=expression, priority=severity, comments=comments)
            return result

        except Exception as e:
            raise AMSZabbixException(self.sanitize_error(e))

    def __del__(self):
        pass