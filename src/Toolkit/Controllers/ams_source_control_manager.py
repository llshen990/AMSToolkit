#!/usr/bin/env /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python
import os
import sys
import argparse
import traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSConfig
from Toolkit.Exceptions import AMSConfigException
from Toolkit.Lib import AMSLogger
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Controllers.tools.SVNStatus import SVNStatus


if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')

    AMSDefaults = AMSDefaults()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--tla", nargs='?', help="Three letter abv for project")
    arg_parser.add_argument("--svn_path", nargs='?', help="Full path to the svn repo you wish to verify")
    arg_parser.add_argument("--config_path", nargs='?', help="The JSON config or root of the workspace")
    arg_parser.add_argument("--command", nargs='?', help="The type of source control check to perform")
    args = arg_parser.parse_args()

    exit_value = 1

    if args.tla and args.svn_path and args.config_path:
        raise AMSConfigException('Please specify either tla and svn_path or config_path')

    if not args.tla and not args.svn_path and not args.config_path:
        arg_parser.print_help()
        arg_parser.exit()

    if args.tla and not args.svn_path:
        raise AMSConfigException('Please specify svn_path with tla')

    if not args.tla and args.svn_path:
        raise AMSConfigException('Please specify tla with svn_path')

    if args.command:
        command = str(args.command.strip())
    else:
        if args.tla and args.svn_path:
            command = 'svn'
        else:
            command = 'git'

    try:
        if args.svn_path and args.tla:
            svn = SVNStatus(None, args.svn_path.strip(), args.tla.strip(), command)
        elif args.config_path:
            config_path = str(args.config_path).strip()

            if os.path.isfile(config_path):
                # if path is to an existing JSON config file
                ams_config = AMSConfig(config_path)
                path = os.path.dirname(config_path)
            else:
                ams_config = AMSConfig(os.path.join(config_path, 'conf', 'amp_config.json'))

            ams_logger.set_debug(ams_config.debug)

            if not ams_config.valid_config:
                raise AMSConfigException("No valid config found at file={}".format(ams_config.config_path))

            root_dir = os.path.dirname(config_path)

            # determine path, tla, and type automatically
            svn = SVNStatus(ams_config, root_dir, ams_config.get_my_environment().tla, command)

        svn.get_status()
        exit_value = 0
    except Exception as e:
        ams_logger.error("Caught an exception: {}".format(e))
        ams_logger.error("Traceback: {}".format(traceback.format_exc()))
        raise

    finally:
        sys.exit(exit_value)
