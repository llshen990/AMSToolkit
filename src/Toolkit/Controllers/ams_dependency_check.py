import os
import sys
import argparse
import traceback
from pydoc import locate

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger, AMSReturnCode
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Exceptions import AMSExceptionNoEventNotification, AMSConfigException
from Toolkit.Config import AMSConfig, AMSDependencyChecker
from Toolkit.Lib.DependencyChecks import *

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
    arg_parser.add_argument("--schedule_name", nargs='?', help="Name schedule with the dependency check to test", required=False)
    arg_parser.add_argument("--dependency_check_name", nargs='?', help="Name of dependency check to test", required=False)
    arg_parser.add_argument("--type", nargs='?', choices=AMSDefaults().dependency_checker_allowed_types, help="Override for dependency type", required=False)
    arg_parser.add_argument("--dependency", nargs='?', help="Override for dependency", required=False)
    arg_parser.add_argument("--max_attempts", nargs='?', type=int, help="Override for max_attempts", required=False)
    arg_parser.add_argument("--attempt_interval", nargs='?', type=int, help="Override for attempt_interval", required=False)
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

    if args.dependency_check_name:
        dependency_check_name = str(args.dependency_check_name).strip()
        ams_logger.debug('dependency_check_name={}'.format(dependency_check_name))
    else:
        dependency_check_name = None
    schedule_name = str(args.schedule_name).strip()
    ams_logger.debug('schedule_name={}'.format(schedule_name))

    exit_value = 1

    try:
        dependency_check = None

        if args.config_file and schedule_name:
            if ams_config.new_config:
                raise AMSExceptionNoEventNotification('Config file of %s does not currently exist.  You must specify a valid config.' % args.config_file)

            schedule = ams_config.get_schedule_by_name(schedule_name)

            if not dependency_check_name:
                dependency_check = None
            elif dependency_check_name in schedule.AMSDependencyChecks:
                dependency_check = schedule.AMSDependencyChecks[dependency_check_name]  # type: AMSDependencyChecker
            else:
                raise AMSConfigException("No dependency check named {} exists in schedule {}".format(dependency_check_name, schedule_name))

        elif not args.type:
            print('Either the --type option or --config_file with a --schedule_name and --dependency_check_name must be specified')
            arg_parser.print_usage()
            raise AMSConfigException('Invalid options')
        else:
            dependency_check = AMSDependencyChecker()
            dependency_check.schedule_name = ''
            dependency_check.max_attempts = 1
            dependency_check.attempt_interval = 1
            dependency_check.dependency = '/tmp'

        if args.type:
            ams_logger.debug('type={}'.format(args.type))
            dependency_check.type = args.type

        if args.dependency:
            ams_logger.debug('dependency={}'.format(args.dependency))
            dependency_check.dependency = args.dependency

        if args.max_attempts:
            ams_logger.debug('max_attempts={}'.format(args.max_attempts))
            dependency_check.max_attempts = args.max_attempts

        if args.attempt_interval:
            ams_logger.debug('attempt_interval={}'.format(args.attempt_interval))
            dependency_check.attempt_interval = args.attempt_interval

        if not dependency_check:
            # check all dependencies
            attempt = 0
            schedule = ams_config.get_schedule_by_name(schedule_name)
            ams_logger.info("{} dependencies exist {}".format(len(schedule.AMSDependencyChecks), schedule.AMSDependencyChecks.keys()))
            ams_logger.info("Checking all dependencies on {} policy={}".format(schedule_name, schedule.dependency_check_policy))
            for dependency_check_config in schedule.AMSDependencyChecks:
                attempt += 1
                dependency_check_type = schedule.AMSDependencyChecks[dependency_check_config].type
                ams_logger.info("#{} checking dependency={} type={}".format(attempt, dependency_check_config, dependency_check_type))
                dependency_tmp = 'AMS' + dependency_check_type + 'DependencyCheck'
                dependency_check_obj = locate('Toolkit.Lib.DependencyChecks.' + dependency_tmp)(ams_config, schedule.AMSDependencyChecks[dependency_check_config])
                temp = dependency_check_obj._check_dependency()
                result = temp
                ams_logger.info("Job success={}".format(result.job_success))

                if not temp.job_success:
                    exit_value = 1
                    if not result.job_success:
                        result.message = dependency_check_obj.commandline_output()

                    if schedule.dependency_check_policy == ams_config.AMSDefaults.available_dependency_check_policies[0]:
                        ams_logger.info("Stopping after first detected dependency failure")
                        break
        else:
            result = dependency_check.check_dependency(ams_config)  # type: AMSReturnCode
            ams_logger.info("Job success={}".format(result.job_success))

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
