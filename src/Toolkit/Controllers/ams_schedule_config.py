import argparse
import logging
import sys
import traceback
import glob
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from Toolkit.Lib import AMSLogger
from Toolkit.Config import AMSConfig, AMSSchedule, AMSProject
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Exceptions import AMSConfigException
from Toolkit.Models import AMSProjectConfig

if __name__ == "__main__":
    ams_schedule_launcher = None

    try:
        arg_parser = argparse.ArgumentParser()
        # noinspection PyTypeChecker
        arg_parser.add_argument("--config_file", nargs='?', type=str, help="Config File", required=True)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--project", nargs='?', type=str, help="Project", required=True)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--schedule", nargs='?', type=str, help="Schedule", required=False)
        # noinspection PyTypeChecker
        arg_parser.add_argument("--directory", nargs='?', type=str, help="Directory", required=False)

        arg_parser.add_argument("--action", nargs='?', choices=['list', 'delete', 'add', 'create'], help="Action to perform", required=True)

        args = arg_parser.parse_args(sys.argv[1:])

        tmp_schedule = str(args.schedule).strip()
        if not tmp_schedule or tmp_schedule is None:
            tmp_schedule = 'unknown_schedule'

        ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '__' + tmp_schedule.replace(os.sep, '_') + '.log')
        ams_defaults = AMSDefaults()

        ams_config = AMSConfig(str(args.config_file).strip())
        ams_logger.set_debug(ams_config.debug)
        if not ams_config.valid_config:
            raise AMSConfigException('Invalid configuration file specified: %s' % args.config_file)

        try:
            my_environment = ams_config.get_my_environment()
        except AMSConfigException as e:
            ams_logger.error('Current hostname=%s does not exist in environment config.  Please define in environment config or check to make sure you are running on correct host: %s.' % (ams_config.my_hostname, str(e)))
            raise

        project = ams_config.AMSProjects[args.project.strip()]

        # add the schedule
        if args.action == 'list':
            print "Schedules in project " + project.project_name + " are:"
            for name in project.AMSSchedules.itervalues():
                print name.schedule_name
            sys.exit(0)

        if args.action == 'delete':
            if not args.schedule:
                print "Schedule must be specified for " + args.action
                sys.exit(0)
            AMSProjectConfig(ams_config, project).remove_schedule(args.schedule.strip())
        elif args.action == 'add':
            if not args.schedule:
                print "Schedule must be specified for " + args.action
                sys.exit(0)
            AMSProjectConfig(ams_config, project).add_schedule(args.schedule.strip())
        else:
            directory = os.getcwd()
            if args.directory:
                directory = args.directory.strip()

            if not FileExistsValidator(True).is_dir(directory):
                print "Directory " + directory + " does not exist"
                sys.exit(0)

            for schedule_name in glob.glob(directory+'/*.xml'):
                AMSProjectConfig(ams_config, project).add_schedule(schedule_name)

    except AMSConfigException as e:
        print 'AMSConfigException encountered: %s' % str(e)
    except Exception as e:

        print 'Exception encountered: %s' % str(e)
        print traceback.print_exc()