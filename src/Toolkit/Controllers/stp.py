import os
import sys
import argparse
import logging
import traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Models import STP
from Toolkit.Exceptions import AMSExceptionNoEventNotification, AMSConfigException
from Toolkit.Config import AMSConfig

os.environ["HTTP_PROXY"] = "http://webproxy.vsp.sas.com:3128"
os.environ["http_proxy"] = "http://webproxy.vsp.sas.com:3128"
os.environ["HTTPS_PROXY"] = "http://webproxy.vsp.sas.com:3128"
os.environ["https_proxy"] = "http://webproxy.vsp.sas.com:3128"

if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--config_file", nargs='?', help="Config File For STP Checks", required=True)
    # noinspection PyTypeChecker
    arg_parser.add_argument("--disable_proxy", action='store_true', help="Disable Proxy?", required=False, default=False)
    # noinspection PyTypeChecker
    arg_parser.add_argument("--disable_zabbix", action='store_true', help="Disable Zabbix?", required=False, default=False)

    args = arg_parser.parse_args(sys.argv[1:])
    ams_logger.debug('config_file=%s' % str(args.config_file).strip())
    ams_config = AMSConfig(str(args.config_file).strip())
    ams_logger.set_debug(ams_config.debug)

    if ams_config.new_config:
        raise AMSExceptionNoEventNotification('Config file of %s does not currently exist.  You must specify a valid config.' % args.config_file)

    do_zabbix = True
    if args.disable_zabbix:
        do_zabbix = False

    if not do_zabbix:
        ams_logger.info('Disabling Zabbix')

    try:
        # Ensure that environment variables are disabled prior to creating STP so that Thycotic uses the correct proxy
        stp = STP(ams_config, use_zabbix=do_zabbix)
        if args.disable_proxy:
            os.environ["HTTP_PROXY"] = ""
            os.environ["http_proxy"] = ""
            os.environ["HTTPS_PROXY"] = ""
            os.environ["https_proxy"] = ""

        mi_result = stp.execute_mi_tests()
        # Removing web tests for now
        web_result = None

        if not mi_result:
            ams_logger.warning('There was no MI Result')
        if not web_result:
            ams_logger.warning('There was no Web Result')

        if (not mi_result or (mi_result and mi_result.is_success())) and (not web_result or (web_result and web_result.is_success())):
            ams_logger.info('Successful STP HealthCheck')
            exit(0)
        else:
            if mi_result:
                ams_logger.info('MI Result %s' % mi_result.format_error_summary())
            if web_result:
                ams_logger.info('Web Result %s' % web_result.format_error_summary())
            ams_logger.error('Failed STP HealthCheck')
    except KeyboardInterrupt:
        print '%sUser termination.  Exiting...' % os.linesep
        exit(0)
    except AMSConfigException as e:
        print 'Config exception occurred: ' + str(e)
    except Exception as e:
        ams_logger.error("Caught an exception: " + str(e))
        ams_logger.error("Traceback: " + traceback.format_exc())
    exit(1)