import os
import sys
import argparse
import logging
import traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Models import AMSSmokeTestModel
from Toolkit.Exceptions import AMSExceptionNoEventNotification, AMSConfigException
from Toolkit.Config import AMSConfig

if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--config_file", nargs='?', help="Config File", required=True)
    arg_parser.add_argument("--host", nargs='?', help="Host to test", required=True)
    arg_parser.add_argument("--service", nargs='?', help="Service to test", required=True)
    arg_parser.add_argument("--test", nargs='?', choices=['up', 'down'], help="Desired test state of the service", required=True)

    args = arg_parser.parse_args(sys.argv[1:])
    ams_logger.debug('config_file=%s' % str(args.config_file).strip())
    ams_config = AMSConfig(str(args.config_file).strip())
    ams_logger.set_debug(ams_config.debug)

    host = str(args.host).strip()
    service = str(args.service).strip()
    test = str(args.test).strip()
    ams_logger.debug('host={}'.format(host))
    ams_logger.debug('service={}'.format(service))
    ams_logger.debug('test={}'.format(test))

    if ams_config.new_config:
        raise AMSExceptionNoEventNotification('Config file of %s does not currently exist.  You must specify a valid config.' % args.config_file)

    exit_value = 1

    try:
        model = AMSSmokeTestModel(ams_config, host, service)
        rval = model.check_health()

        if test == 'up' and rval == True:
            ams_logger.info('SUCCESS! Expected service {} to be {} and it is {}'.format(service, test, test))
            exit_value = 0
        elif test == 'down' and rval == False:
            ams_logger.info('SUCCESS! Expected service {} to be {} and it is {}'.format(service, test, test))
            exit_value = 0
        else:
            ams_logger.info('FAILURE! Expected service {} to be {} on host {} and it is not {}'.format(service, test, host, test))

    except KeyboardInterrupt:
        print('%sUser termination.  Exiting...'.format(os.linesep))
    except AMSConfigException as e:
        print('Config exception occurred: ' + str(e))
    except Exception as e:
        ams_logger.error("Caught an exception: {}".format(e))
        ams_logger.error("Traceback: {}".format(traceback.format_exc()))
        raise

    finally:
        sys.exit(exit_value)
