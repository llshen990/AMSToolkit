import os
import sys
import getpass
import logging
import traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Config import AMSConfig

if __name__ == "__main__":
    ams_logger = None
    try:
        ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
        if len(sys.argv) > 1 and sys.argv[1] == '--decrypt':
            print(AMSConfig().decrypt(raw_input("Phrase to decrypt: ")))
        else:
            print(AMSConfig().encrypt(getpass.getpass("Phrase to encrypt: ")))
    except KeyboardInterrupt:
        print '%sExiting...' % os.linesep
    except Exception as e:
        if ams_logger:
            ams_logger.error("Caught an exception: " + str(e))
            ams_logger.error("Traceback: " + traceback.format_exc())
        raise