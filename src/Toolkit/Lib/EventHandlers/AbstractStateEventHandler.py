import sys
import logging
import abc
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

class AbstractStateEventHandler(object):
    automation_name = 'automation.name'
    automation_type = 'automation.type'
    batch_info = 'batch.info'
    batch_runtime = 'batch.runtime'
    batch_delay = 'batch.delay'
    batch_config = 'batch.config'
    batch_config_raw = 'batch.config.raw'
    batch_error = 'batch.error'
    batch_initial_value = '0'
    batch_error_value = '1'
    batch_start_value = '1'
    batch_end_value = '0'
    batch_delay_value = '0'
    batch_running = 'batch.running'
    AMSLogger = logging.getLogger('AMS')
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.AMSLogger = logging.getLogger('AMS')
        pass


    @abc.abstractmethod
    def _before_start(self):
        pass

    @abc.abstractmethod
    def _on_dependency(self, info):
        pass

    @abc.abstractmethod
    def _on_start(self):
        pass

    @abc.abstractmethod
    def _on_error(self):
        pass

    @abc.abstractmethod
    def _on_info(self, info):
        pass

    @abc.abstractmethod
    def _on_finish(self):
        pass

    @abc.abstractmethod
    def _after_finish(self):
        pass

    @abc.abstractmethod
    def _on_batch_delay(self):
        pass

    def before_start(self):
        # @todo: implement any logic that applies to all File/ScheduleEventHandlers.  Raise AMSScheduleEventHandlerException on errors.
        return self._before_start()

    def on_dependency(self, info):
        # @todo: implement any logic that applies to all File/ScheduleEventHandlers.  Raise AMSScheduleEventHandlerException on errors.
        self._on_dependency(info)

    def on_start(self):
        # @todo: implement any logic that applies to all File/ScheduleEventHandlers.  Raise AMSScheduleEventHandlerException on errors.
        self._on_start()

    def on_error(self):
        # @todo: implement any logic that applies to all File/ScheduleEventHandlers.  Raise AMSScheduleEventHandlerException on errors.
        self._on_error()

    def on_info(self, info):
        # @todo: implement any logic that applies to all File/ScheduleEventHandlers.  Raise AMSScheduleEventHandlerException on errors.
        self._on_info(info)

    def on_finish(self):
        # @todo: implement any logic that applies to all File/ScheduleEventHandlers.  Raise AMSScheduleEventHandlerException on errors.
        self._on_finish()

    def after_finish(self):
        # @todo: implement any logic that applies to all File/ScheduleEventHandlers.  Raise AMSScheduleEventHandlerException on errors.
        self._after_finish()

    def on_batch_delay(self):
        # @todo: implement any logic that applies to all File/ScheduleEventHandlers.  Raise AMSScheduleEventHandlerException on errors.
        self._on_batch_delay()

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

    def __del__(self):
        # @todo: write bundle cache to disk
        pass