import logging
import subprocess
import sys
import threading
import time
import logging
import concurrent.futures
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

import Toolkit.Lib
import Toolkit.MetaClasses
from Toolkit.Lib.EventHandlers import AbstractEventHandler
from Toolkit.Config import AMSJibbixOptions, AMSConfig, AMSSchedule
from Toolkit.Exceptions import AMSAttributeMapperInfoException, AMSException
from Toolkit.Lib.Helpers import OutputFormatHelper
from Toolkit.Lib.AMSScriptReturnCode import AMSScriptReturnCode

DEFAULT_MAX_WORKERS = 20  # type: int
TIMER_CHECK_INTERVAL = 30  # type: int


def do_future_submit(script_path, jibbix_options=None, command_line_args=[], cwd=None):
    process_args = str(script_path).split(' ')
    if command_line_args:
        for arg in command_line_args:
            arg = str(arg).strip()
            if arg:
                process_args.append(arg)

    logger = logging.getLogger('AMS')
    logger.debug('CWD is: %s' % cwd)

    if jibbix_options is None:
        logger.debug("No jibbix_options are defined for submitted future script_path=" + script_path)

    logger.info('Script to execute: %s' % " ".join(process_args))
    logger.debug('CWD=%s' % cwd)

    try:
        p = subprocess.Popen(process_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, cwd=cwd)
        # start the future
        logger.info("Exec'd pid=" + str(p.pid) + " args=" + str(process_args))
        std_out, std_err = p.communicate()

        # print when finished
        logger.info("Finished pid=" + str(p.pid) + "\nstd_out=" + std_out.strip() + "\nstd_err=" + std_err.strip() + "\nrc=" + str(p.returncode))
    except Exception as e:
        logger.error('Caught an exception when trying to run the command for script[%s]: %s - %s' % (script_path, OutputFormatHelper.join_output_from_list(process_args), str(e)))
        return Toolkit.Lib.AMSScriptReturnCode(-1, 1, '', str(e), script_path)

    # build the returncode object
    return Toolkit.Lib.AMSScriptReturnCode(p.pid, p.returncode, std_out.strip(), std_err.strip(), script_path)


class AMSMultiThread(object):
    """
    This class implements a multiprocessor executor that keeps track of executed futures.

    Completed futures that contain errors send notifications using the configured EventHandler and jibbixoptions.
    """
    __metaclass__ = Toolkit.MetaClasses.Singleton

    def create(self, ams_config=None, max_workers=DEFAULT_MAX_WORKERS, timer_interval=TIMER_CHECK_INTERVAL):
        self.timer_interval = timer_interval
        self.max_workers = max_workers
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers)
        self.futures = {}
        try:
            self.event_handler = AbstractEventHandler.create_handler(ams_config)  # type: AbstractEventHandler
        except AMSAttributeMapperInfoException:
            self.AMSLogger.warning('No valid event_handler specified')
            self.event_handler = None

    def __init__(self, ams_config=None, max_workers=DEFAULT_MAX_WORKERS, timer_interval=TIMER_CHECK_INTERVAL):
        self.ams_attribute_mapper = None
        self.timer_interval = None
        self.max_workers = None
        self.cleaner = None
        self.executor = None
        self.futures = None
        self.AMSLogger = logging.getLogger('AMS')
        self.event_handler = None
        self.create(ams_config, max_workers, timer_interval)

    def handle_done(self, future):
        if future.callback_method:
            self.AMSLogger.debug('In callback object')
            return future.callback_method(future.result())

        result = future.result()  # type: AMSScriptReturnCode
        self.AMSLogger.info(result.get_message())

        # If the result has errors, then alert as needed with AMSLogger
        if result.is_error():
            self.AMSLogger.critical(result.format_errors())
            if future.jibbix_options:
                try:
                    self.event_handler.create(future.jibbix_options, summary=result.format_error_summary(), description=result.format_errors())
                except Exception as e:
                    self.AMSLogger.error('Event handler failed to properly communicate error: %s' % str(e))

    def check_futures(self):
        self.AMSLogger.debug("<<<Current jobs>>>")
        now = time.time()
        # Ensure the cleaner timer is cancelled before we do any more work
        self.cleaner.cancel()

        # Iterate through the list of running futures
        for group_name, group_futures in self.futures.iteritems():
            for future in group_futures:
                # print out some handy information on running futures
                runtime = int(now - future.start_time)
                self.AMSLogger.debug("script_path=" + str(future.script_path) + " group_name=" + str(group_name) + " running=" + str(future.running()) + " runtime=" + str(runtime) + " secs" + ' longtime=%s seconds' % future.long_running_seconds)

                # future.long_running_seconds = long_running_seconds
                # future.schedule = schedule
                if future.done():
                    # Remove the future first and then call the handle_done function
                    group_futures.remove(future)
                    self.handle_done(future)
                else:
                    self.AMSLogger.debug("Job is not complete")
                    # self.AMSLogger.debug("future.long_running_seconds=%s" % future.long_running_seconds)
                    # self.AMSLogger.debug("future.AMSSchedule=%s" % future.AMSSchedule)
                    # self.AMSLogger.debug("future.AMSConfig=%s" % future.AMSConfig)
                    # self.AMSLogger.debug("future.long_running_callback=%s" % future.long_running_callback)
                    # self.AMSLogger.debug("future.long_running_fired=%s" % future.long_running_fired)
                    # self.AMSLogger.debug("runtime=%s" % runtime)
                    # self.AMSLogger.debug("future.long_running_seconds=%s" % future.long_running_seconds)

                    if future.long_running_seconds is not None and future.AMSSchedule is not None and future.AMSConfig is not None and future.long_running_callback is not None and not future.long_running_fired and runtime > future.long_running_seconds > 0:
                        self.AMSLogger.info('Firing longtime warning...elapsed time of %s seconds is longer than longtime threshold of %s seconds.' % (runtime, future.long_running_seconds))
                        future.long_running_callback()
                        future.long_running_fired = True
                        group_futures.remove(future)
                        group_futures.append(future)

        # restart the check_futures timer
        self.cleaner = threading.Timer(self.timer_interval, self.check_futures)
        self.cleaner.start()

    def get_future_num_by_group(self, group_name):
        if group_name in self.futures:
            return len(self.futures[group_name])
        return 0

    def run_job(self, script_path, jibbix_options=None, group_name=None, command_line_args=[], long_running_callback=None, callback_method=None, cwd=None, long_running_seconds=None, schedule=None, ams_config=None):
        # submit the future with the given values
        self.AMSLogger.debug("Submitting group_name=" + str(group_name) + " script_path=" + str(script_path) + " jibbix_options=" + str(jibbix_options))
        self.AMSLogger.debug("Command line args=%s" % ",".join(command_line_args))
        # Lazy create the cleaner so we don't have a timer thread running around if we don't get shutdown called
        if not self.cleaner:
            self.AMSLogger.debug("Starting cleaner thread")
            self.cleaner = threading.Timer(self.timer_interval, self.check_futures)
            self.cleaner.start()
        future = self.executor.submit(do_future_submit, script_path, jibbix_options, command_line_args, cwd)

        # record these values when the future is started
        future.start_time = time.time()
        future.script_path = script_path
        future.jibbix_options = jibbix_options  # type: AMSJibbixOptions
        future.long_running_callback = long_running_callback
        future.callback_method = callback_method
        future.long_running_seconds = long_running_seconds
        future.AMSSchedule = schedule  # type: AMSSchedule
        future.AMSConfig = ams_config  # type: AMSConfig
        future.long_running_fired = False

        # add the futures to list of submitted futures
        if group_name in self.futures:
            future_list = self.futures[group_name]
            self.AMSLogger.debug("Appending group_name=" + str(group_name) + " for future=" + str(future) + " to existing future_list=" + str(future_list))
            future_list.append(future)
        else:
            self.AMSLogger.debug("Creating group_name=" + str(group_name) + " for future=" + str(future))
            self.futures[group_name] = [future]

        return future

    def has_jobs(self):
        if not self.cleaner:
            return False
        return self.cleaner.is_alive()

    def shutdown(self, wait=True):
        # attempt to gracefully stop the timer
        if self.cleaner and self.cleaner.is_alive() and wait:
            self.AMSLogger.info("Cancelling any remaining jobs.")
            try:
                self.cleaner.cancel()
            except Exception as e:
                self.AMSLogger.info("Caught exception cancelling jobs %s" % str(e))
        else:
            self.AMSLogger.info("Not cancelling jobs")

        # Iterate through the list of running futures and cancel any running futures
        if self.futures:
            self.AMSLogger.info("Current jobs at time of shutdown:")
            for group_name, group_futures in self.futures.iteritems():
                for future in group_futures:
                    # print out some handy information on running futures
                    self.AMSLogger.info("script_path=" + str(future.script_path) + " state=" + str(future._state) + " start=" + str(time.asctime( time.localtime(future.start_time))))
        else:
            self.AMSLogger.info("No jobs at time of shutdown")

        if not wait:
            self.AMSLogger.info("Shutting down executor")
        else:
            self.AMSLogger.info("Shutdown called waiting for jobs to terminate")

        # Shutdown the executor and optionally wait to ensure the tasks complete
        if self.executor:
            self.executor.shutdown(wait)
        else:
            self.AMSLogger.info("No executor so not calling shutdown")

        self.AMSLogger.info("Executor terminated")

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        self.executor.shutdown(wait=False)
