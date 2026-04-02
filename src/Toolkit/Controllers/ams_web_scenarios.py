import os
import sys
import argparse
import logging
import traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Models import AMSWebScenarioModel
from Toolkit.Exceptions import AMSExceptionNoEventNotification, AMSConfigException
from Toolkit.Config import AMSConfig, AMSAttributeMapper

if __name__ == "__main__":
    ams_attribute_mapper = AMSAttributeMapper()

    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--config_file", nargs='?', help="Config File", required=True)
    arg_parser.add_argument("--web_scenario_name", nargs='?', help="Web Scenario name", required=True)

    args = arg_parser.parse_args(sys.argv[1:])
    ams_logger.debug('config_file=%s' % str(args.config_file).strip())
    ams_config = AMSConfig(str(args.config_file).strip())
    ams_logger.set_debug(ams_config.debug)

    web_scenario_name = str(args.web_scenario_name).strip()
    ams_logger.debug('web_scenario_name=%s' % web_scenario_name)

    if ams_config.new_config:
        raise AMSExceptionNoEventNotification('Config file of %s does not currently exist.  You must specify a valid config.' % args.config_file)

    try:
        model = AMSWebScenarioModel(ams_config, web_scenario_name)
        print 'Result of web scenario %s is %s' % (str(web_scenario_name), str(model.check_web_scenario()))
    except KeyboardInterrupt:
        print '%sUser termination.  Exiting...' % os.linesep
    except AMSConfigException as e:
        print 'Config exception occurred: ' + str(e)
    except Exception as e:
        ams_logger.error("Caught an exception: " + str(e))
        ams_logger.error("Traceback: " + traceback.format_exc())

        web_scenario = ams_config.get_web_scenario_by_name(web_scenario_name)
        if web_scenario.AMSJibbixOptions:
            description = "Error message: %s" % str(e)
            description += "\n\nStack Trace:\n"
            description += traceback.format_exc()

            event_handler = ams_attribute_mapper.get_attribute('global_ams_event_handler')
            ams_logger.debug('event_handler=%s' % str(event_handler))
            event_handler.create(web_scenario.AMSJibbixOptions, summary="AMS Web Scenario failed: %s" % web_scenario_name, description=description)

        raise
