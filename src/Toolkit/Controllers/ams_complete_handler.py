import os
import sys
import argparse
import json
import traceback
import distutils

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger, AMSReturnCode
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Exceptions import AMSExceptionNoEventNotification, AMSConfigException
from Toolkit.Config import AMSConfig, AMSCompleteHandler, AMSSuccessCompleteHandler, AMSErrorCompleteHandler

def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--config_file", nargs='?', help="Config File", required=False)
    arg_parser.add_argument("--schedule_name", nargs='?', help="Name schedule with the complete handler to test", required=False)
    arg_parser.add_argument("--complete_handler_name", nargs='?', help="Name of complete handler to test", required=False)
    arg_parser.add_argument("--type", nargs='?', choices=AMSDefaults().complete_handler_allowed_types, help="Override for complete handler type", required=False)
    arg_parser.add_argument("--complete_handler", nargs='?', help="Override for completion handler", required=False)
    arg_parser.add_argument("--service_params", nargs='?', help="Override for service_parms (JSON)", required=False)
    arg_parser.add_argument("--is_success", nargs='?', type=lambda x:bool(str2bool(x)), const=True, help="Override for specifying as success or failure handler", required=False)
    arg_parser.add_argument("--no_logger_output", nargs='?', type=lambda x:bool(str2bool(x)), default=False, const=True, help="Override for specifying no logger output", required=False)

    args = arg_parser.parse_args(sys.argv[1:])
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log', quiet=args.no_logger_output)

    ams_logger.debug('config_file=%s' % str(args.config_file).strip())
    if args.config_file:
        ams_config = AMSConfig(str(args.config_file).strip())
        ams_logger.set_debug(True)
    else:
        ams_config = AMSConfig('')
        ams_logger.set_debug(True)

    complete_handler_name = str(args.complete_handler_name).strip()
    ams_logger.debug('complete_handler_name={}'.format(complete_handler_name))
    schedule_name = str(args.schedule_name).strip()
    ams_logger.debug('schedule_name={}'.format(schedule_name))

    exit_value = 1

    try:
        complete_handler = None
        is_success = None

        if args.config_file and schedule_name and complete_handler_name:
            if ams_config.new_config:
                raise AMSExceptionNoEventNotification('Config file of %s does not currently exist.  You must specify a valid config.' % args.config_file)

            schedule = ams_config.get_schedule_by_name(schedule_name)

            if complete_handler_name in schedule.AMSSuccessCompleteHandler:
                is_success = True
                complete_handler = schedule.AMSSuccessCompleteHandler[complete_handler_name]  # type: AMSCompleteHandler
            elif complete_handler_name in schedule.AMSErrorCompleteHandler:
                is_success = False
                complete_handler = schedule.AMSErrorCompleteHandler[complete_handler_name]  # type: AMSCompleteHandler
            else:
                raise AMSConfigException("No complete handler named {} exists in schedule {}".format(complete_handler_name, schedule_name))

        elif not args.type:
            print('Either the --type option or --config_file with a --schedule_name and --dependency_check_name must be specified')
            arg_parser.print_usage()
            raise AMSConfigException('Invalid options')
        else:
            complete_handler = AMSCompleteHandler()
            complete_handler.schedule_name = ''
            complete_handler.complete_handler = ''

        if args.type:
            ams_logger.debug('type={}'.format(args.type))
            complete_handler.type = args.type

        if args.complete_handler:
            ams_logger.debug('complete_handler={}'.format(args.complete_handler))
            complete_handler.complete_handler = args.complete_handler

        if args.service_params:
            ams_logger.debug('service_params={}'.format(json.loads(args.service_params)))
            complete_handler.service_params = json.loads(args.service_params)

        if args.is_success is not None:
            ams_logger.debug('is_success={}'.format(args.is_success))
            is_success = args.complete_handler

        result = complete_handler.check_complete_handler(ams_config, is_success)  # type: AMSReturnCode
        print('{}'.format(result.get_message()))
        if result.job_success:
            exit_value = 0

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
