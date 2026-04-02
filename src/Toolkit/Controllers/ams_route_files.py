import argparse
import logging
import sys
import traceback

import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Models.AMSRouteFiles import AMSRouteFiles
from Toolkit.Config import AMSConfig, AMSFileRoute, AMSAttributeMapper
from Toolkit.Exceptions import AMSExceptionNoEventNotification
from Toolkit.Lib.Helpers import ProcCheck
from Toolkit.Lib.Defaults import AMSDefaults

if __name__ == "__main__":
    os.environ["HTTP_PROXY"] = \
        os.environ["http_proxy"] = \
        os.environ["HTTPS_PROXY"] = \
        os.environ["https_proxy"] = \
        AMSDefaults().default_web_proxy

    ams_attribute_mapper = AMSAttributeMapper()

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--config_file", nargs='?', type=str, help="Config File", required=True)
    # noinspection PyTypeChecker
    arg_parser.add_argument("--file_route_name", nargs='?', type=str, help="File Route Name", required=True)

    args = arg_parser.parse_args(sys.argv[1:])
    file_route_name = args.file_route_name
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '_' + file_route_name + '.log')
    ams_config = AMSConfig(str(args.config_file).strip())

    ams_logger.set_debug(ams_config.debug)

    if ams_config.new_config:
        raise AMSExceptionNoEventNotification('Config file of %s does not currently exist.  You must specify a valid config.' % args.config_file)

    if not file_route_name:
        raise AMSExceptionNoEventNotification('You must specify a file route name.')

    # initiate the proc check.
    proc_check = ProcCheck(controller_name=__file__, context=file_route_name)
    if not proc_check.lock():
        raise Exception('File Route {} is currently locked. Please check the process and {} file as needed'.format(file_route_name, proc_check.lock_file_name))

    ams_route_files = None
    exit_code = 0

    try:
        ams_route_files = AMSRouteFiles(ams_config, file_route_name)
        ams_route_files.start_file_routing()
    except KeyboardInterrupt:
        print '%sUser killed process with ctrl+c...' % os.linesep
        # noinspection PyUnboundLocalVariable
        exit_code = 128
    except AMSExceptionNoEventNotification as e:
        print "%sProcess exited with a AMSExceptionNoEventNotification exception: %s%s" % (os.linesep, str(e), os.linesep)
        # noinspection PyUnboundLocalVariable
        exit_code = 1
    except Exception as e:
        # noinspection PyUnboundLocalVariable
        ams_logger.error("Caught an exception running %s: %s" % (__file__, str(e)))
        ams_logger.error("Traceback: " + traceback.format_exc())

        description = "Error message: %s" % str(e)
        description += "\n\nStack Trace:\n"
        description += traceback.format_exc()

        event_handler = ams_attribute_mapper.get_attribute('global_ams_event_handler')
        ams_logger.debug('event_handler=%s' % str(event_handler))
        ams_file_route_config = ams_config.get_file_route_by_name(file_route_name)  # type:AMSFileRoute
        event_handler.create(ams_file_route_config.AMSJibbixOptions, summary="AMS File route failed: %s" % file_route_name, description=description)

        # Try and stop the route, but it may not actually be created
        exit_code = 1
    finally:
        # Remove lock file
        if proc_check:
            proc_check.unlock()
        # noinspection PyUnboundLocalVariable
        if ams_route_files:
            ams_route_files.stop_file_routing(exit_code)
        sys.exit(exit_code)