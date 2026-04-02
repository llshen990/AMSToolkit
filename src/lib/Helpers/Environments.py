import os.path, sys, ConfigParser, socket, json, ast

from datetime import datetime, timedelta

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Exceptions import EnvironmentException


class Environments(object):
    """
    This class defines the markets / environments
    """

    def __init__(self):
        # get config options
        self.config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        self.config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        self.environments = {}
        self.all_markets = []
        self.environment_optimal_run_date = {}
        if self.config.has_section('MARKETS'):
            tmp_envs = self.config._sections['MARKETS']
            del tmp_envs['__name__']
            for env in tmp_envs:
                env_upper = str(env).upper()
                self.environments[env_upper] = ast.literal_eval(tmp_envs[env])
                self.all_markets.append(env_upper)
        else:
            raise EnvironmentException('Config does not have MARKETS config section.')

        self.my_market = self.config.get('DEFAULT', 'market_config_section')
        self.my_hostname = str(socket.gethostname()).strip()
        if self.my_hostname == 'sasdev1-centos6':
            self.my_hostname = 'wmt06au'
        if self.config.has_option('ENV_HOSTNAME_LOOKUP', self.my_hostname):
            self.my_environment = self.config.get('ENV_HOSTNAME_LOOKUP', self.my_hostname)
        else:
            raise EnvironmentException('Config does not have ENV_HOSTNAME_LOOKUP option')

    def get_market_fiendly_name(self, market):
        market = str(market).strip().upper()
        if market not in self.environments:
            return 'Unknown Market of: ' + market

        if 'name' not in self.environments[market]:
            return market + ' does not have a friendly name'

        return self.environments[market]['name']

    def get_optimal_run_date(self, market):
        market = str(market).strip().upper()
        if market not in self.environments:
            raise EnvironmentException('Unknown Market of: ' + market)

        if 'transaction_lag' not in self.environments[market]:
            raise EnvironmentException(market + ' does not have a transaction_lag configured')

        return (datetime.today() - timedelta(days=int(self.environments[market]['transaction_lag']))).strftime('%Y%m%d')

    def days_behind_batch(self, market, current_run_date_obj):
        optimal_run_date_obj = datetime.strptime(self.get_optimal_run_date(market), '%Y%m%d')
        delta = optimal_run_date_obj - current_run_date_obj
        return delta.days

    def get_reporting_libname_stmt(self, market=None):
        ret_str = ''
        if market:
            market = str(market).strip().upper()
            if market not in self.environments:
                raise EnvironmentException('Unknown Market of: ' + market)
        else:
            market = self.my_market

        if 'reporting_lib' not in self.environments[market]:
            raise EnvironmentException(market + ' does not have a reporting_lib configured')

        ret_str = "libname %s oracle authdomain='%s' path=\"%s\";" % (self.environments[market]['reporting_lib']['libname'], self.environments[market]['reporting_lib']['authdomain'], self.environments[market]['reporting_lib']['path'])

        if 'other_meta_libs' in self.environments[market]:
            for k, v in self.environments[market]['other_meta_libs'].iteritems():
                ret_str += os.linesep + v

        return ret_str

    def validate_market(self, market):
        if not market:
            raise EnvironmentException('In order to validate market, market name required.')

        if market not in self.environments:
            raise EnvironmentException("Invalid market: " + str(market))

        return True

    def __str__(self):
        print 'my_market: ' + self.my_market
        print 'my_hostname: ' + self.my_hostname
        print 'my_environment: ' + self.my_environment
        print 'my_market_friendly_name: ' + self.get_market_fiendly_name(self.my_market)
        print 'I should be running transaction date: ' + self.get_optimal_run_date(self.my_market)
        print 'environments: ' + json.dumps(self.environments, indent=4)
        print 'environments: ' + json.dumps(self.environments[self.my_market.upper()], indent=4)
        print 'all_markets: ' + json.dumps(self.all_markets, indent=4)
        return ''
