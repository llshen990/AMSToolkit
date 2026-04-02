# @author owhoyt

import os.path, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)


class StopBatchTriggerZabbixBatchDelayException(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super(StopBatchTriggerZabbixBatchDelayException, self).__init__(message)

        # we are no longer going to trigger the manual hold
        # from lib.Helpers import BatchTriggers
        # BatchTriggers().create_batch_delay_trigger_file()
        pass
