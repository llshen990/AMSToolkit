import argparse
import logging
import sys
import traceback
import os
import re

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Models.AMSFileHandler import AMSFileHandlerModel
from Toolkit.Config import AMSConfig, AMSAttributeMapper
from Toolkit.Exceptions import AMSExceptionNoEventNotification

if __name__ == "__main__":

    ams_attribute_mapper = AMSAttributeMapper()

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--config_file", nargs='?', type=str, help="Config File", required=True)
    # noinspection PyTypeChecker
    arg_parser.add_argument("--file_handler_name", nargs='?', type=str, help="File Handler Name", required=True)

    args = arg_parser.parse_args(sys.argv[1:])
    file_handler_name = args.file_handler_name

    if not file_handler_name:
        raise AMSExceptionNoEventNotification('You must specify a file handler name.')

    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '-' + re.sub(r' |' + os.sep, '_', file_handler_name))
    ams_config = AMSConfig(str(args.config_file).strip())
    ams_logger.set_debug(ams_config.debug)

    if ams_config.new_config:
        raise AMSExceptionNoEventNotification('Config file of %s does not currently exist.  You must specify a valid config.' % args.config_file)

    try:
        ams_file_handler = AMSFileHandlerModel(ams_config, file_handler_name)
        ams_file_handler.execute_file_handler()
    except KeyboardInterrupt:
        print '%sUser killed process with ctrl+c...' % os.linesep
        # noinspection PyUnboundLocalVariable
        # ams_route_files.stop_file_routing()
    except AMSExceptionNoEventNotification as e:
        print "%sProcess exited with a AMSExceptionNoEventNotification exception: %s%s" % (os.linesep, str(e), os.linesep)
        # noinspection PyUnboundLocalVariable
        # ams_route_files.stop_file_routing()
    except Exception as e:
        # noinspection PyUnboundLocalVariable
        # ams_route_files.stop_file_routing(True)

        ams_logger.error("Caught an exception running %s: %s" % (__file__, str(e)))
        ams_logger.error("Traceback: " + traceback.format_exc())

        event_handler = ams_attribute_mapper.get_attribute('global_ams_event_handler')
        ams_logger.debug('event_handler=%s' % str(event_handler))
        sys.exit(1)
    finally:
        # noinspection PyUnboundLocalVariable
        # ams_route_files.stop_file_routing()
        sys.exit(0)
