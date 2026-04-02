import os
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Views import CommandLineConfigView
from Toolkit.Lib import AMSLogger
from Toolkit.Exceptions import AMSConfigSyntaxException
import logging
import traceback

if __name__ == "__main__":

    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')

    try:
        command_line_config_view = CommandLineConfigView()
        command_line_config_view.set_input_data(sys.argv[1:])
        command_line_config_view.init()
        command_line_config_view.render()
        command_line_config_view.ams_config.write_config()
    except KeyboardInterrupt:
        print '%sNo config changes have been saved due to user termination.  Exiting...' % os.linesep
    except AMSConfigSyntaxException as e:
        ams_logger.error('Caught exception with permissions or syntax of config file: %s' % str(e))
    except Exception as e:
        ams_logger.error("Caught an exception running the configuration generator: " + str(e))
        ams_logger.error("Traceback: " + traceback.format_exc())
        raise