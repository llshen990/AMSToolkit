import argparse
import sys
import traceback
import re
import os
from os import path
from datetime import datetime

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Config import AMSConfig
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Models import AMSScheduleLauncher
from Toolkit.Exceptions import AMSConfigException, AMSDependencyCheckException
from Toolkit.Lib.Helpers import ProcCheck
from lib.Validators import FileExistsValidator
from Toolkit.Lib.Helpers import AMSTouch

if __name__ == "__main__":
    proc_check = None
    ams_schedule_launcher = None

    try:
        arg_parser = argparse.ArgumentParser()
        # noinspection PyTypeChecker
        arg_parser.add_argument("--config_file", nargs='?', type=str, help="Config File", required=True)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--schedule", nargs='?', type=str, help="Schedule", required=True)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--project", nargs='?', type=str, help="Project", required=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--adhoc_schedule", nargs='?', type=str, help="Adhoc Schedule to use (overrides configured schedule)", required=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--resume", action='store_true', help="Resume Schedule", required=False, default=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--trigger_file", nargs='?', type=str, help="Require the specified trigger file before launching the schedule", required=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--trigger_script", nargs='?', type=str, help="Run the defined trigger script before launching the schedule", required=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--longtime", nargs='?', type=int, help="Longtime in seconds to alert if schedule is still running", required=False, default=-1)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--shorttime", nargs='?', type=int, help="Shortime in seconds to alert if schedule is still running", required=False, default=-1)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--skip_dependencies", action='store_true', help="Skips all configured dependency checks", required=False, default=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--skip_complete_handlers", action='store_true', help="Skips all configured complete handlers", required=False, default=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--skip_lock_file", action='store_true', help="Skips creating and checking of lock file", required=False, default=False)

        args = arg_parser.parse_args()

        tmp_schedule = args.schedule.strip()
        if not tmp_schedule or tmp_schedule is None:
            tmp_schedule = 'unknown_schedule'

        ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '__' + re.sub('\s', '_', tmp_schedule.replace(os.sep, '_')) + '.log')
        ams_defaults = AMSDefaults()

        try:
            ams_config = AMSConfig(str(args.config_file).strip())
            ams_logger.set_debug(ams_config.debug)
            raised_exception = None
        except Exception as e:
            raised_exception = e
            ams_config = AMSConfig()

        try:
            my_environment = ams_config.get_my_environment()
        except AMSConfigException as e:
            ams_logger.error('Current hostname=%s does not exist in environment config.  Please define in environment config or check to make sure you are running on correct host: %s.' % (ams_config.my_hostname, str(e)))
            raise

        ams_schedule_launcher = AMSScheduleLauncher(ams_config)

        proc_check = ProcCheck(controller_name=__file__, context=tmp_schedule, lock_dir=ams_config.get_signal_directory_by_schedule_name(tmp_schedule))
        last_run_file = proc_check.lock_file_name + '.last_run'
        if path.exists(last_run_file):
            last_update = (datetime.fromtimestamp(os.stat(last_run_file).st_mtime))
        else:
            last_update = 0

        ams_schedule_launcher.validate_args(args)

        ams_logger.info('Last run at {}'.format(last_update))
        if not args.skip_lock_file:
            # initiate the proc check.
            ams_logger.info('Running check on lock file {}'.format(proc_check.lock_file_name))
            if not proc_check.lock():
                if last_update:
                    raise AMSConfigException(
                        "This schedule is currently locked: {}\nPlease check the process and this file as needed: {}\n\nIt is possible the schedule is still in progress from the most recent run, started: {}\n\n".format(tmp_schedule, proc_check.lock_file_name, last_update))
                else:
                    raise AMSConfigException(
                        "This schedule is currently locked: {}\nPlease check the process and this file as needed: {}\n\nIt is possible the schedule is still in progress from the most recent run.\n\n".format(tmp_schedule, proc_check.lock_file_name))
        else:
            ams_logger.info('Skipping check on lock file for schedule {}'.format(tmp_schedule))
            if FileExistsValidator.is_readable(proc_check.lock_file_name):
                ams_logger.warning('Lock file {} exists!!'.format(proc_check.lock_file_name))
            else:
                ams_logger.info('Lock file {} does not exist!!'.format(proc_check.lock_file_name))

        if not ams_config.valid_config:
            raise AMSConfigException('Invalid configuration file specified: %s' % args.config_file)

        if raised_exception:
            raise raised_exception

        AMSTouch.touch(last_run_file)
        ams_schedule_launcher.launch_schedule()

    except AMSDependencyCheckException as e:
        print 'Failed dependency check: %s' % str(e)
    except Exception as e:
        print 'Exception encountered: %s' % str(e)
        print traceback.print_exc()
        # noinspection PyUnboundLocalVariable
        ams_schedule_launcher.stop_schedule(raised_exception=e)
    finally:
        if ams_schedule_launcher:
            ams_schedule_launcher.end_schedule()
        # Remove lock file
        if proc_check:
            proc_check.unlock()