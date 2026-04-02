from zeep import Client
from requests import Session
from datetime import datetime
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.

from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from Toolkit.Lib.Helpers import FileSoapTransport
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Lib import AMSWebReturnCode


class AMSMIHealthCheckModel(AbstractAMSBase):
    def __init__(self, ams_config, mi_healthcheck, username=None, password=None):
        AbstractAMSBase.__init__(self, ams_config)
        self.mi_healthcheck = mi_healthcheck
        self.session = Session()
        self.health = AMSWebReturnCode(self.mi_healthcheck.midtier_url)

        proxies = {}
        if self.mi_healthcheck.http_proxy is not None:
            proxies['http_proxy'] = self.mi_healthcheck.http_proxy
            self.AMSConfig.AMSLogger.info('Using http_proxy=%s' % self.mi_healthcheck.http_proxy)

        if self.mi_healthcheck.https_proxy is not None:
            proxies['https_proxy'] = self.mi_healthcheck.https_proxy
            self.AMSConfig.AMSLogger.info('Using https_proxy=%s' % self.mi_healthcheck.https_proxy)

        if len(proxies) is 0:
            self.AMSConfig.AMSLogger.info('Using no defined http or https proxies')

        # Set proxies for session
        self.session.proxies = proxies

        # Use the username and password on the mi_healthcheck as default
        if not username:
            username = mi_healthcheck.AMSSecret.username

        if username:
            self.AMSConfig.AMSLogger.info("Checking MI Health username=<" + ams_config.decrypt(username) + ">")

        if not password:
            password = mi_healthcheck.AMSSecret.password

        # Set auth for session if available
        if username and password:
            self.session.auth = HTTPBasicAuth(ams_config.decrypt(username), ams_config.decrypt(password))
        else:
            self.AMSConfig.AMSLogger.warning("No username or password specified so not setting any basic auth info in session")

    def _check_config_service(self):
        data = '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" ' \
               'xmlns:xsd="http://www.w3.org/2001/XMLSchema" ' \
               'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' \
               '<soapenv:Body>' \
               '<getSystemLocale soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">' \
               '</getSystemLocale>' \
               '</soapenv:Body>' \
               '</soapenv:Envelope>'
        headers = {'SOAPAction': 'getSystemLocale', 'Content-Type': 'text/xml'}
        full_url = self.mi_healthcheck.midtier_url + '/miserver/services/ConfigService'

        self.AMSConfig.AMSLogger.info('Checking config service health url=%s' % full_url)

        response = self.session.post(url=full_url, data=data, verify=self.mi_healthcheck.verify_ssl, timeout=self.mi_healthcheck.timeout, headers=headers)

        self.AMSConfig.AMSLogger.info('Config service response status_code=%s' % response.status_code)
        self.AMSConfig.AMSLogger.debug('Config service response text=%s\n' % response.text)

        self.health.status_code = response.status_code

        # Any 200 HTTP response code indicates success
        if response.status_code == 200:
            self.health.add_message('Check for /miserver/services/ConfigService passed.')
            self.health.job_success = True
        else:
            self.health.add_error('Check for /miserver/services/ConfigService failed.')

    def _check_pko_service(self):
        full_url = self.mi_healthcheck.midtier_url + '/miserver/services/PKOService?wsdl'
        self.AMSConfig.AMSLogger.info('Checking PKO service health url=%s' % full_url)

        try:
            transport = FileSoapTransport(session=self.session)
            client = Client(full_url, transport=transport)
            response = client.service.checkRequest(1)

            # Any response that authenticates is a valid response
            # Typically this will return an integer value
            self.AMSConfig.AMSLogger.info('PKO service response=%s' % str(response))
            self.health.add_message('Check for /miserver/services/PKOService passed.')
            self.health.job_success = True

            # There is no real status_code on the response so make it 200 if it succeeds
            self.health.status_code = '200'
            return
        except Exception as e:
            # I suspect that this exception won't always mean the check failed
            # So we'll have to find some exceptions that mean the PKOService is not
            # installed or not available and return True instead

            # The service is there, but is not licensed?
            if str(e.message).find('com.sas.solutions.di.server.license.api.LicenseException') != -1:
                self.AMSConfig.AMSLogger.info('PKO service is not licensed so returning True')
                self.health.add_message('Check for /miserver/services/PKOService is not licensed so it is passed.')
                self.health.job_success = True

                # There is no real status_code on the response so make it 200 if it succeeds
                self.health.status_code = '200'
            else:
                self.health.add_message('Check for /miserver/services/PKOService failed.')
                # There is no real status_code on the response so make it 400 if it fails
                self.health.status_code = '400'
                self.AMSConfig.AMSLogger.error('Problem checking midtier health url=%s' % self.mi_healthcheck.midtier_url)
        return

    def check_health(self, use_zabbix=True):
        if use_zabbix:
            zabbix = AMSZabbix(self.AMSLogger, config=self.AMSConfig, hostname=self.mi_healthcheck.hostname)
        else:
            zabbix = None

        try:
            # Removed LLD, consider replacing this with creating items as in Controllers/stp
            self.AMSConfig.AMSLogger.info('Checking midtier health url=%s' % self.mi_healthcheck.midtier_url)

            start_time = datetime.now()

            self._check_config_service()
            if self.health.is_success():
                self._check_pko_service()

            return self.health

        # noinspection PyBroadException
        except Exception as e:
            self.AMSConfig.AMSLogger.error('Problem checking midtier health url=%s' % self.mi_healthcheck.midtier_url)
            self.health.status_code = 504
            self.health.add_error('Exception encountered sending request: %s' % str(e))
            return self.health

        finally:
            # TODO: I'm going to hack in the zabbix calls here.
            # After this is checked in, I'll refactor the caller of this and the webscenario model to return the same returncode
            # and handle the zabbix stuff in the same place in the same manner.
            if zabbix is not None:
                zabbix.call_zabbix_sender('healthCheck.MI.result', '1' if self.health.job_success else '0')
                # Removed this item for now as we don't really need it
                # zabbix.call_zabbix_sender('healthCheck.MI.status', str(self.health.status_code))
                zabbix.call_zabbix_sender('healthCheck.MI.message', self.health.message if self.health.job_success else self.health.format_errors())
                # Removed this item for now as we don't really need it
                # zabbix.call_zabbix_sender('healthCheck.MI.runTime', str((datetime.now() - start_time).total_seconds()))
