from pydoc import locate

from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from Toolkit.Exceptions import AMSConfigException
from Toolkit.Lib import AMSReturnCode
from Toolkit.Lib.Helpers import AMSUtils
from Toolkit.Thycotic import AMSSecretServer


class AMSSmokeTestModel(AbstractAMSBase):
    def __init__(self, ams_config, host, service):
        AbstractAMSBase.__init__(self, ams_config)
        self.host = host
        self.AMSEnvironment = ams_config.get_environment_by_name(host)
        self.service = service

    def check_health(self):
        try:
            rval = False

            if self.service in self.AMSEnvironment.service:
                params = self.AMSEnvironment.service[self.service]
                if 'port' in params:
                    port = params['port']
                else:
                    port = 80

                if str(self.service).startswith('midtier'):
                    secret = None
                    if 'secret' in params:
                        secret = params['secret']
                        try:
                            ams_secret = self.AMSConfig.get_secret_by_name(secret)
                            secret_server = AMSSecretServer(self.AMSConfig,username=self.AMSConfig.decrypt(ams_secret.username), password=self.AMSConfig.decrypt(ams_secret.password), domain=ams_secret.domain, https_proxy=ams_secret.https_proxy)
                            secret = secret_server.get_amspassword_secret(ams_secret.secret_id)
                        except Exception as e:
                            secret = None
                            self.AMSConfig.AMSLogger.warning('Problem finding secret {} '.format(e))
                    else:
                        self.AMSConfig.AMSLogger.error('No secret configured for midtier on {}. A secret is required.'.format(self.host))
                        return rval

                    path = '/miserver/services'
                    if 'path' in params:
                        path = params['path']
                    else:
                        self.AMSConfig.AMSLogger.warning('No path configured for midtier on {} using default path={}'.format(self.host, path))

                    model = locate('Toolkit.Models.AMSMidtierSmokeTestModel')(self.AMSConfig, secret)
                    rval = model.check_health('http://{}:{}/{}'.format(self.host, port, path)).job_success
                else:
                    rval = AMSUtils.check_tcp_port(self.host, port)

            else:
                raise AMSConfigException("Service {} not configured for environment {}".format(self.service, self.host))

            return rval

        # noinspection PyBroadException
        except Exception as e:
            self.AMSConfig.AMSLogger.error('Problem checking service {} on host {}'.format(self.service, self.host))
            health = AMSReturnCode()
            health.add_error('Exception encountered sending request: %s' % str(e))
            return health