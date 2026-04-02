from zeep import Client
from requests import Session
from datetime import datetime
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.

from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from Toolkit.Lib.Helpers import FileSoapTransport
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Lib import AMSReturnCode, AMSWebReturnCode
from Toolkit.Config import AMSMIHealthCheck


class AMSMidtierSmokeTestModel(AbstractAMSBase):
    def __init__(self, ams_config, secret=None, verify_ssl=True, timeout=300, http_proxy=None, https_proxy=None, username=None, password=None):
        AbstractAMSBase.__init__(self, ams_config)
        self.session = Session()
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        proxies = {}
        if http_proxy is not None:
            proxies['http_proxy'] = http_proxy
            self.AMSConfig.AMSLogger.info('Using http_proxy=%s' % http_proxy)

        if https_proxy is not None:
            proxies['https_proxy'] = https_proxy
            self.AMSConfig.AMSLogger.info('Using https_proxy=%s' % https_proxy)

        if len(proxies) is 0:
            self.AMSConfig.AMSLogger.info('Using no defined http or https proxies')

        # Set proxies for session
        self.session.proxies = proxies

        # Use the username and password on the mi_healthcheck as default
        if not username and secret:
            username = secret.username

        if username:
            self.AMSConfig.AMSLogger.info("Checking MI Health username=<" + ams_config.decrypt(username) + ">")

        if not password and secret:
            password = secret.password

        # Set auth for session if available
        if username and password:
            self.session.auth = HTTPBasicAuth(ams_config.decrypt(username), ams_config.decrypt(password))
        else:
            self.AMSConfig.AMSLogger.warning("No username or password specified so not setting any basic auth info in session")

    def _check_config_service(self, health, midtier_url_base):
        data = '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" ' \
               'xmlns:xsd="http://www.w3.org/2001/XMLSchema" ' \
               'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' \
               '<soapenv:Body>' \
               '<getSystemLocale soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">' \
               '</getSystemLocale>' \
               '</soapenv:Body>' \
               '</soapenv:Envelope>'
        headers = {'SOAPAction': 'getSystemLocale', 'Content-Type': 'text/xml'}
        full_url = midtier_url_base + '/ConfigService'

        self.AMSConfig.AMSLogger.info('Checking config service health url=%s' % full_url)

        response = self.session.post(url=full_url, data=data, verify=self.verify_ssl, timeout=self.timeout, headers=headers)

        self.AMSConfig.AMSLogger.info('Config service response status_code=%s' % response.status_code)
        self.AMSConfig.AMSLogger.debug('Config service response text=%s\n' % response.text)

        health.status_code = response.status_code

        # Any 200 HTTP response code indicates success
        if response.status_code == 200:
            health.add_message('Check for ConfigService passed.')
            health.job_success = True
        else:
            health.add_error('Check for ConfigService failed.')

    def _check_pko_service(self, health, midtier_url_base):
        full_url = midtier_url_base + '/PKOService?wsdl'
        self.AMSConfig.AMSLogger.info('Checking PKO service health url=%s' % full_url)

        try:
            transport = FileSoapTransport(session=self.session)
            client = Client(full_url, transport=transport)
            response = client.service.checkRequest(1)

            # Any response that authenticates is a valid response
            # Typically this will return an integer value
            self.AMSConfig.AMSLogger.info('PKO service response=%s' % str(response))
            health.add_message('Check for PKOService passed.')
            health.job_success = True

            # There is no real status_code on the response so make it 200 if it succeeds
            health.status_code = '200'
            return
        except Exception as e:
            # I suspect that this exception won't always mean the check failed
            # So we'll have to find some exceptions that mean the PKOService is not
            # installed or not available and return True instead

            # The service is there, but is not licensed?
            if str(e.message).find('com.sas.solutions.di.server.license.api.LicenseException') != -1:
                self.AMSConfig.AMSLogger.info('PKO service is not licensed so returning True')
                health.add_message('Check for PKOService is not licensed so it is passed.')
                health.job_success = True

                # There is no real status_code on the response so make it 200 if it succeeds
                health.status_code = '200'
            else:
                health.add_message('Check for PKOService failed.')
                # There is no real status_code on the response so make it 400 if it fails
                health.status_code = '400'
                self.AMSConfig.AMSLogger.error('Problem checking midtier health url={}'.format(midtier_url_base))
        return

    def check_health(self, midtier_url_base):
        health = None

        try:
            health = AMSWebReturnCode(url=midtier_url_base)

            self.AMSConfig.AMSLogger.info('Checking midtier health url={}'.format(midtier_url_base))

            self._check_config_service(health, midtier_url_base)
            if health.is_success():
                self._check_pko_service(health, midtier_url_base)

            return health

        # noinspection PyBroadException
        except Exception as e:
            self.AMSConfig.AMSLogger.error('Problem checking midtier health url=%s'.format(midtier_url_base))
            health = AMSReturnCode()
            health.add_error('Exception encountered sending request: %s' % str(e))
            return health