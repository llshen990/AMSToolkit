import math
import sys
import os
import time
import traceback
from datetime import datetime

from paramiko import AuthenticationException

from Toolkit.Config import AMSConfig
from Toolkit.Config import AMSFileRoute, AMSDependencyChecker
from Toolkit.Exceptions import AMSFatalException
from Toolkit.Lib.RoutingMethods import *
from Toolkit.Lib.FileEventHandlers import *
from Toolkit.Lib.EventHandlers import AbstractEventHandler
from Toolkit.Lib import AMSMultiThread, AMSReturnCode, AMSScriptReturnCode
from Toolkit.Lib.DependencyChecks import *
from Toolkit.Models import AbstractAMSBase

DEFAULT_RETRY_WAIT = 30
DEFAULT_RETRY_LIMIT = 5
DEFAULT_POLLING_INTERVAL = 300
DEFAULT_MAX_ITERATIONS = 10
DEFAULT_RECURSION_LIMIT = math.floor(sys.getrecursionlimit() * .9)
RESET_CONNECTION_POLLING_INTERVAL_LIMIT = 100
MAX_ALLOWED_SKIP_RECURSION_LIMIT = math.floor(sys.getrecursionlimit() * .05)


class AMSRouteFiles(AbstractAMSBase):

    def __init__(self, ams_config, file_route_by_name):
        """
        This is the initi method to instantiate an AMSRouteFiles object.
        :param ams_config: Loaded AMSConfig object.
        :type ams_config: AMSConfig
        :param file_route_by_name: File route name to refer to the config.
        :type file_route_by_name: str
        """

        AbstractAMSBase.__init__(self, ams_config)

        self.ams_file_route_config = self.AMSConfig.get_file_route_by_name(file_route_by_name)  # type:AMSFileRoute
        self.polling_interval = self.ams_file_route_config.polling_interval  # to check the incoming directory in secs
        self.retry_limit = self.ams_file_route_config.retry_limit  # how many times to try copying
        self.retry_wait = self.ams_file_route_config.retry_wait  # how many seconds to wait before trying to copy
        self.num_retries = 0
        self.routing_method_obj = None
        self.__recursion_cntr = 0
        self.__max_recursion_skips = 0
        self.route_event_handler = AbstractAMSFileRouteEventHandler.create_handler(self.AMSLogger, self.AMSConfig,
                                                                                     file_route_by_name)

        if file_route_by_name and file_route_by_name in ams_config.AMSFileRoutes:
            self.AMSFileRoute = ams_config.AMSFileRoutes[file_route_by_name]  # type: AMSFileRoute
        else:
            self.AMSFileRoute = None
        self.failed_dependencies = {}


        self.event_handler = AbstractEventHandler.create_handler(ams_config)
        try:
            self.retry_wait = int(self.retry_wait)
        except ValueError:
            self.AMSLogger.warning("Invalid entry for retry_wait: %s using %s seconds." % (self.retry_wait, DEFAULT_RETRY_WAIT))
            self.retry_wait = DEFAULT_RETRY_WAIT

        try:
            self.retry_limit = int(self.retry_limit)
        except ValueError:
            self.AMSLogger.warning("Invalid entry for retry_limit: %s using %s attempts." % (self.retry_limit, DEFAULT_RETRY_LIMIT))
            self.retry_limit = DEFAULT_RETRY_LIMIT

        try:
            self.polling_interval = int(self.polling_interval)
        except ValueError:
            self.AMSLogger.warning("Invalid entry for polling_interval: %s using %s seconds." % (self.polling_interval, DEFAULT_POLLING_INTERVAL))
            self.polling_interval = DEFAULT_POLLING_INTERVAL

    def _check_dependencies(self):
        self.AMSLogger.info('Checking Dependencies...')
        result = None
        if self.AMSFileRoute and len(self.AMSFileRoute.AMSDependencyChecks) > 0:
            self.route_event_handler.on_info("Checking {} Dependencies policy='{}'".format(len(self.AMSFileRoute.AMSDependencyChecks), self.AMSFileRoute.dependency_check_policy))
            for dependency_check_name, ams_dependency_check_config in self.AMSFileRoute.AMSDependencyChecks.iteritems():  # type: str, AMSDependencyChecker
                self.AMSLogger.debug('Checking dependency: %s' % dependency_check_name)
                dependency = self._check_dependency(ams_dependency_check_config)
                if dependency:
                    dependency.display_job_status()
                    if not result:
                        result = dependency
                    else:
                        result.add_result(dependency)

                    if result.is_error():
                        self.route_event_handler.on_info("Dependency {}[{}] failed".format(dependency_check_name, ams_dependency_check_config.type))
                    else:
                        self.route_event_handler.on_info("Dependency {}[{}] succeeded".format(dependency_check_name, ams_dependency_check_config.type))

                    # Be sure to check the result of this specific dependency check for evaluating the fail first policy
                    if dependency.is_error() and self.AMSFileRoute.dependency_check_policy == self.AMSDefaults.available_dependency_check_policies[0]:
                        self.AMSLogger.info("Stopping dependency check after first discovered failure")
                        break

            if len(self.failed_dependencies) > 0:
                self.AMSLogger.info('dependencies failed')
                some_text = '\n'
                for dependency_name, dependency_dict in self.failed_dependencies.iteritems():  # type: str, dict
                    ams_return_code = dependency_dict['result']  # type: AMSReturnCode
                    ams_dependency_check_config = dependency_dict['config']  # type: AMSDependencyChecker
                    some_text += 'Dependency %s[%s] failed: %s%s' % (
                        dependency_name, ams_dependency_check_config.type, ams_return_code.get_message(), os.linesep)
                    if isinstance(ams_return_code, AMSScriptReturnCode) and len(ams_return_code.std_err):
                        some_text += '{}'.format(ams_return_code.std_err)
                self.route_event_handler.on_info(some_text)
                self.route_event_handler.on_info("dependencies failed")

                if self.AMSFileRoute.AMSJibbixOptions and self.AMSFileRoute.AMSJibbixOptions.project:
                    self._throw_failed_dependencies(result)
                else:
                    self.AMSLogger.warning('Skipping dependencies notification because no project is configured')
                return False
            else:
                self.AMSLogger.info('dependencies succeeded')
                self.route_event_handler.on_info("dependencies succeeded")

        else:
            self.AMSLogger.info('No Dependencies configured...')

        return True

    def _check_dependency(self, ams_dependency_check_config):
        """
        This method will fire off a dependency check in a separate thread and monitor the results
        :param ams_dependency_check_config: Dependency check config
        :type ams_dependency_check_config: AMSDependencyChecker
        :return: True upon success, false on failure
        :rtype: bool
        """
        self.route_event_handler.on_dependency("{}[{}]".format(ams_dependency_check_config.dependency_check_name, ams_dependency_check_config.type))
        self.AMSLogger.debug('In __check_dependency for %s' % ams_dependency_check_config.dependency_check_name)
        dependency_tmp = 'AMS' + ams_dependency_check_config.type + 'DependencyCheck'
        dependency_check_obj = globals()[dependency_tmp](self.AMSConfig,
                                                         ams_dependency_check_config)  # type: AbstractAMSDependencyCheck
        dependency_res = dependency_check_obj.evaluate_dependency()
        if not dependency_res.is_success():
            self.failed_dependencies[ams_dependency_check_config.dependency_check_name] = {
                'config': ams_dependency_check_config,
                'object': dependency_check_obj,
                'result': dependency_res
            }
            return dependency_res

        return dependency_res

    def _throw_failed_dependencies(self, result):
        self.complete_time = datetime.now()
        exception_str = ''
        for dependency_name, dependency_dict in self.failed_dependencies.iteritems():  # type: str, dict
            if exception_str:
                exception_str += os.linesep

            ams_dependency_check_config = dependency_dict['config']  # type: AMSDependencyChecker
            dependency_check_obj = dependency_dict['object']  # type: AbstractAMSDependencyCheck
            exception_str += 'Dependency %s[%s] failed: %s%s%s' % (
                dependency_name, ams_dependency_check_config.type, ams_dependency_check_config.dependency, os.linesep,
                os.linesep)
            exception_str += dependency_check_obj.instructions_for_verification()

            if result:
                exception_str += result.format_errors() + os.linesep + os.linesep

            if ams_dependency_check_config.details:
                exception_str += '{}{}{}'.format(ams_dependency_check_config.details, os.linesep, os.linesep)
            if ams_dependency_check_config.runbook_sub_link:
                exception_str += 'Dependency Runbook Link: {}{}{}'.format(ams_dependency_check_config.runbook_sub_link, os.linesep, os.linesep)

        self.event_handler.create(self.AMSFileRoute.AMSJibbixOptions, None, self._build_failed_dependencies_event_summary(), exception_str)

    def _build_failed_dependencies_event_summary(self):
        return '%s File Route has failed at least one dependency check' % self.AMSFileRoute.file_route_name

    def execute_route_files(self):
        self.AMSLogger.debug('In execute_route_files().')

        routing_method_tmp = 'AMS' + self.ams_file_route_config.AMSFileRouteMethod.type + 'Method'

        self.AMSLogger.debug('Starting routing method=%s' % routing_method_tmp)

        if not self.routing_method_obj:
            self.AMSLogger.debug('Connecting file route method=%s' % routing_method_tmp)
            self.routing_method_obj = globals()[routing_method_tmp](self.AMSConfig, self.ams_file_route_config.AMSFileRouteMethod, self.ams_file_route_config.AMSJibbixOptions)  # type: AbstractAMSMethod

        self.routing_method_obj.setup()

        self.routing_method_obj.route()

        if self.routing_method_obj.routed_files:
            self.route_event_handler.on_info('Routed {} files: {}.'.format(len(self.routing_method_obj.routed_files), self.routing_method_obj.routed_files))
        else:
            self.route_event_handler.on_info('Routed 0 files.')

        return True

    def start_file_routing(self):
        # check for dependency checks
        if self.__recursion_cntr == 0:
            self.route_event_handler.before_start()
            self.route_event_handler.on_start()

        if self._check_dependencies():
            pass
        else:
            self.AMSLogger.info("Exiting without running FileRoute")
            exit(1)

        global DEFAULT_MAX_ITERATIONS
        exit_upon_finish = False
        iterations = 1
        self.__recursion_cntr += 1
        if self.polling_interval >= RESET_CONNECTION_POLLING_INTERVAL_LIMIT or self.polling_interval < 1:
            DEFAULT_MAX_ITERATIONS = 2
            exit_upon_finish = True
        while iterations < DEFAULT_MAX_ITERATIONS:
            try:
                # checking recursion limit
                self.__check_recursion_limit()
                self.AMSLogger.info("Starting iteration #%s.  Looking for files to route... " % iterations)
                self.execute_route_files()
                if (iterations + 1) <= DEFAULT_MAX_ITERATIONS and not exit_upon_finish:
                    self.AMSLogger.info("Ending iteration #%s." % iterations)
                    self.AMSLogger.info("Sleeping polling interval=%s." % self.polling_interval)
                    time.sleep(self.polling_interval)
                else:
                    self.AMSLogger.info("Ending last iteration #%s." % iterations)
                self.num_retries = 0
                iterations += 1
            except AMSFatalException as e:
                self.AMSLogger.error('[FATAL] %s' % str(e))
                self.route_event_handler.on_error()
                raise
            except AuthenticationException:
                self.AMSLogger.error('[FATAL] Could not authenticate.')
                self.route_event_handler.on_error()
                raise
            except Exception as e:
                self.AMSLogger.critical('Caught an error when routing files: %s' % str(e))
                self.AMSLogger.debug(traceback.format_exc())
                self.AMSLogger.info('Retry limit is set to %s.  Num retries is currently %s.  Sleeping for the retry wait of %s and trying again: ' % (self.retry_limit, self.num_retries, self.retry_wait))
                if self.retry_limit > 0 and self.num_retries < self.retry_limit:
                    time.sleep(self.retry_wait)
                    self.num_retries += 1
                elif 0 < self.retry_limit <= self.num_retries:
                    self.AMSLogger.error('Caught exception while routing files and we have hit the max retry limit: %s' % str(e))
                    self.route_event_handler.on_error()
                    raise
                else:
                    self.AMSLogger.error('Caught exception while routing files and the retry limit was not enabled: %s' % str(e))
                    self.route_event_handler.on_error()
                    raise

        # Force route to reconnect
        self.routing_method_obj = None

        if not exit_upon_finish:
            self.start_file_routing()
        else:
            self.route_event_handler.on_finish()
            self.route_event_handler.after_finish()

    def __check_recursion_limit(self):
        self.AMSLogger.debug('Checking recursion limit: current=%s max=%s' % (self.__recursion_cntr, DEFAULT_RECURSION_LIMIT))
        if self.__recursion_cntr >= DEFAULT_RECURSION_LIMIT:
            if self.__max_recursion_skips >= MAX_ALLOWED_SKIP_RECURSION_LIMIT:
                self.AMSLogger.debug('Reached default recursion limit of %s and max skips %s, must end immediately.' % (DEFAULT_RECURSION_LIMIT, MAX_ALLOWED_SKIP_RECURSION_LIMIT))
                self.stop_file_routing()
            elif self.polling_interval >= 59:
                self.AMSLogger.debug('Reached default recursion limit of %s.  Gracefully exiting as the next polling interval is % seconds' % (DEFAULT_RECURSION_LIMIT, self.polling_interval))
                self.stop_file_routing()
            else:
                dt = datetime.now()
                self.AMSLogger.debug('Current seconds: %s' % dt.second)
                self.AMSLogger.debug('Polling Interval: %s' % self.polling_interval)
                if math.floor((59 - dt.second) / self.polling_interval) < 1:
                    if AMSMultiThread().has_jobs() > 0 and self.__max_recursion_skips < MAX_ALLOWED_SKIP_RECURSION_LIMIT:
                        self.AMSLogger.debug('There are futures running...')
                        self.__max_recursion_skips += 1
                        self.AMSLogger.debug('Incrementing max_recursion_skips...new val=%s.  Allowed to skip %s total times' % (self.__max_recursion_skips, MAX_ALLOWED_SKIP_RECURSION_LIMIT))
                    else:
                        self.AMSLogger.debug('Reached default recursion limit of %s.  There is less than 1 polling interval left of %s seconds.  Gracefully exiting.' % (DEFAULT_RECURSION_LIMIT, self.polling_interval))
                        self.stop_file_routing(exit_code=1)
                else:
                    self.AMSLogger.debug('Reached default recursion limit of %s.  Gracefully exiting.' % DEFAULT_RECURSION_LIMIT)
                    self.stop_file_routing()

    def stop_file_routing(self, exit_code=0):
        self.AMSLogger.info("Shutting down routing method and exiting...")
        try:
            AMSMultiThread().shutdown()
        except Exception as e:
            self.AMSLogger.info("Caught exception shutting down routing method and exiting...%s" % str(e))
