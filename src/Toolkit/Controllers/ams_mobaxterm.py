import os
import sys
import argparse


APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Models.AMSMobaXterm import AMSMobaXtermModel
import logging
import traceback

if __name__ == "__main__":
    try:
        ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
        ams_logger.set_debug(True)
        arg_parser = argparse.ArgumentParser()
        # noinspection PyTypeChecker
        arg_parser.add_argument("--tlas", nargs='?', help="Comma separated list of TLAs", required=True)

        args = arg_parser.parse_args(sys.argv[1:])
        tlas = str(args.tlas).strip().split(',')

        ams_logger.debug('tla=%s' % tlas)

        model = AMSMobaXtermModel()
        for tla in tlas:
            try:
                model.generate_config(tla.upper())
                print("Generated for {}".format(tla))
            except Exception as e:
                print("Can't generate for TLA {}, error is {}".format(tla, e))

    except KeyboardInterrupt:
        print '%sExiting...' % os.linesep
    except Exception as e:
        ams_logger.error("Caught an exception: " + str(e))
        ams_logger.error("Traceback: " + traceback.format_exc())
        raise