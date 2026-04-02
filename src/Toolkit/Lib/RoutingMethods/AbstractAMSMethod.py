import datetime
import shutil
import sys
import logging
import abc
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSFileRouteMethod, AMSAttributeMapper, AMSJibbixOptions
from Toolkit.Exceptions import AMSFatalException, AMSMethodException
from Toolkit.Lib.EventHandlers import AbstractEventHandler
from lib.Validators import RegExValidator, FileExistsValidator
from Toolkit.Lib.AMSMultiThread import AMSMultiThread
from Toolkit.Lib import AMSScriptReturnCode

class AbstractAMSMethod(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, ams_config, config, jibbix_options):
        """
        :param config: Loaded AMS Config Object.
        :type config: AMSFileRouteDestinationMethod
        """
        # Doesn't seem like we need the config for anything so we'll remove this if that's true

        self.AMSConfig = ams_config
        self.config = config  # type: AMSFileRouteMethod
        self._matching_files = []
        self._found_files = []
        self._found_files_validated = False
        self._matching_files_validated = False
        self._regex_validator = RegExValidator(True)
        self._to_tmp_folder = None  # type: str
        self.AMSLogger = logging.getLogger('AMS')
        self.fev = FileExistsValidator(True)
        self._files_in_error = {}
        self.event_handler = AbstractEventHandler.create_handler(ams_config)

        self.AMSLogger.debug('event_handler=%s' % str(self.event_handler))
        self.jibbix_options = jibbix_options  # type: AMSJibbixOptions
        self._modified_interval = 2
        self.routed_files = []


    @abc.abstractmethod
    def _get_file_list(self):
        pass

    @abc.abstractmethod
    def _check_and_create_target_to_dir(self):
        pass

    @abc.abstractmethod
    def _check_and_create_target_tmp_dir(self):
        pass

    @abc.abstractmethod
    def _check_remote_final_target(self, final_target):
        pass

    @abc.abstractmethod
    def _route_tmp(self, source_file, to_path_tmp):
        pass

    @abc.abstractmethod
    def _route_final(self, source_file, final_target, to_path_tmp):
        pass

    @abc.abstractmethod
    def _remove_source_file(self, source_file):
        pass

    @abc.abstractmethod
    def _check_modified_time(self, filename):
        """
        :rtype: float
        """
        pass

    def setup(self):
        self._matching_files = []
        self._found_files = []
        self._found_files_validated = False
        self._matching_files_validated = False
        if self.config and self.config.http_proxy:
            os.environ["HTTP_PROXY"] = os.environ["http_proxy"] = self.config.http_proxy
        if self.config and self.config.https_proxy:
            os.environ["HTTPS_PROXY"] = os.environ["https_proxy"] = self.config.https_proxy
        # self._files_in_error = {} # want this to stay so we can keep the failed files over multiple iterations of the loop for retry logic.

    @staticmethod
    def shutdown():
        AMSMultiThread().shutdown()

    def get_num_on_success_handlers(self):
        return AMSMultiThread(self.AMSConfig).get_future_num_by_group(self.config.file_route_name)

    def route(self):
        """
        This method will be the interface into routing a file for all methods.
        :return: True upon success, Exception upon error.
        :rtype: bool
        """
        self._to_tmp_folder = os.path.join(self.config.to_directory, 'ghusps-in-process')

        if not self._get_file_list():
            self.AMSLogger.debug('Did not find any files to route.  Returning...')
            return False

        if not self._validate_found_files():
            return False

        if not self._found_files_validated:
            raise AMSFatalException('You need to call _validate_found_files() in your implementation of get_file_list() on %s' % self.__whoami())

        if not self._matching_files_validated:
            raise AMSFatalException('You need to call _match_found_files() in your implementation of get_file_list() on %s' % self.__whoami())

        if not self._check_and_create_target_to_dir():
            raise AMSFatalException('Could not _check_and_create_target_to_dir()')

        if not self._check_and_create_target_tmp_dir():
            raise AMSFatalException('Could not _check_and_create_target_tmp_dir()')

        self.AMSLogger.debug('Attempting to route %s files via %s to %s' % (len(self._matching_files), self.config.type, self.config.host))
        for source_file in self._matching_files:
            final_target = os.path.join(self.config.to_directory, source_file)
            to_path_tmp = self._get_tmp_path(self._to_tmp_folder, source_file)
            try:
                final_target_stat = self._check_remote_final_target(final_target)
                source_file_ready = self._check_ready(os.path.join(self.config.from_directory, source_file))
                if final_target_stat:
                    if self.config.overwrite:
                        self.AMSLogger.warning('File already exists at the final target but overwrite is %s: %s' % (self.config.overwrite, final_target))
                    else:
                        self.AMSLogger.info('[SKIP] File already exists at the final target and overwrite is %s: %s' % (self.config.overwrite, final_target))
                        continue
                if source_file_ready:
                    try:
                        self.AMSLogger.debug('Routing file=%s to temp directory=%s' % (source_file, to_path_tmp))
                        self._route_tmp(source_file, to_path_tmp)
                    except AMSFatalException:
                        raise
                    except Exception as e:
                        self._record_failed_file(source_file, '_route_tmp(): Could not route source_file=%s to to_path_tmp=%s.  Exception=%s' % (source_file, to_path_tmp, str(e)))
                        continue

                    try:
                        self.AMSLogger.info('Routing file=%s to directory=%s' % (source_file, final_target))
                        self._route_final(source_file, final_target, to_path_tmp)
                        self.routed_files.append((source_file, final_target))
                    except AMSFatalException:
                        raise
                    except Exception as e:
                        self._record_failed_file(source_file, '_route_final(): Could not route source_file=%s to final target=%s, to_path_tmp=%s.  Exception=%s' % (source_file, final_target, to_path_tmp, str(e)))
                        continue

                    try:
                        self.AMSLogger.debug('Trying _archive(%s)' % source_file)
                        self.AMSLogger.debug('Method type: %s' % self.config.type)
                        if self.config.type in ['ADLSPull', 'SftpPull', 'S3Pull']:
                            if self._archive(to_path_tmp):
                                os.remove(to_path_tmp)
                        else:
                            self._archive(source_file)
                    except AMSFatalException:
                        raise
                    except Exception as e:
                        self._record_failed_file(source_file, '_archive(): Could not archive source_file=%s to archive dir=%s.  Exception=%s' % (source_file, self.config.archive_directory, str(e)))
                        continue

                    self._success_handler(source_file, final_target)

                    try:
                        self.AMSLogger.debug('Trying _remove_source_file(%s)' % source_file)
                        self._remove_source_file(source_file)
                    except AMSFatalException:
                        raise
                    except Exception as e:
                        self._record_failed_file(source_file, '_remove_from_file(): Could not remove source_file=%s.  Exception=%s' % (source_file, str(e)))
                        continue

                    self._remove_file_in_error(source_file)
                else:
                    self.AMSLogger.info('[SKIP] File has been modified recently: {}'.format(source_file))
                    continue
            except AMSFatalException:
                raise
            except Exception as e:
                self._record_failed_file(source_file, 'route(): Caught unknown exception when routing source_file=%s. Exception=%s' % (source_file, str(e)))

    def _check_ready(self, source_file):
        delta = datetime.timedelta(seconds=self._modified_interval)
        mod_time = datetime.datetime.fromtimestamp(self._check_modified_time(source_file))
        now = datetime.datetime.now()
        if now - mod_time > delta:
            return True
        else:
            self.AMSLogger.debug('File ({}) has been modified recently, will not attempt transfer.'.format(source_file))
            return False

    def _remove_file_in_error(self, source_file):
        if source_file in self._files_in_error:
            del self._files_in_error[source_file]

    def _record_failed_file(self, source_file, err_msg):
        fire_event = False
        if source_file not in self._files_in_error:
            self._files_in_error[source_file] = err_msg
            fire_event = True
        elif source_file in self._files_in_error and err_msg != self._files_in_error[source_file]:
            self._files_in_error[source_file] = err_msg
            fire_event = True

        if fire_event:
            summary = '[%s Failed] %s' % (str(type(self).__name__), source_file)
            err_msg += "\n\n"
            err_msg += 'File Route Name: %s' % self.config.file_route_name
            self.event_handler.create(self.jibbix_options, summary=summary, description=err_msg)

        self.AMSLogger.critical('[FAILED] %s' % err_msg)
        return True

    def _archive(self, source_file):
        if not self.config.archive_directory:
            self.AMSLogger.debug('Not archiving %s as the archive directory is not set in the config.' % source_file)
            return False

        self._make_archive_dir()

        if self.fev.directory_writeable(self.config.archive_directory):
            full_source_path = os.path.join(self.config.from_directory, source_file)
            self.AMSLogger.info('Archiving %s to %s' % (full_source_path, self.config.archive_directory))
            shutil.copy(full_source_path, self.config.archive_directory)
            return True
        else:
            self.AMSLogger.critical('Could not archive file=%s because archive dir=%s does not exist or is not writeable' % (source_file, self.config.archive_directory))
            raise AMSMethodException('Could not archive file=%s' % source_file)

    def _make_archive_dir(self):
        return self._method_make_dir(self.config.archive_directory)

    def _method_make_dir(self, directory):
        self.AMSLogger.debug('In _method_make_dir(%s)' % directory)

        if not directory:
            self.AMSLogger.debug('1')
            return False

        if not self.fev.directory_exists(directory):
            self.AMSLogger.debug('2')
            os.makedirs(directory)

        if not self.fev.directory_readable(directory) or not self.fev.directory_writeable(directory):
            self.AMSLogger.debug('3')
            os.chmod(directory, 0775)

        return True

    def _validate_found_files(self):
        self.AMSLogger.debug('in AbstractAMSMethod::_validate_found_files()')
        self.AMSLogger.debug('Going to loop through self._found_files')
        tmp_found_list = []
        tmp_match_list = []
        for f in self._found_files:
            self.AMSLogger.debug('raw f=%s' % f)
            f = str(f).strip()
            self.AMSLogger.debug('stripped f=%s' % f)
            if f:
                self.AMSLogger.debug('appending %s to tmp_found_list' % f)
                tmp_found_list.append(f)

            if self._match_found_files(f):
                self.AMSLogger.debug('appending %s to tmp_match_list' % f)
                tmp_match_list.append(f)

        self._found_files = tmp_found_list
        self._matching_files = tmp_match_list
        self._found_files_validated = True
        found_files_len = len(self._found_files)
        matching_files_len = len(self._matching_files)
        if found_files_len < 1:
            self.AMSLogger.debug('found_files_len=0')
            return False
        elif matching_files_len < 1:
            self.AMSLogger.debug('matching_files_len=0')
            return False

        return True

    def _match_found_files(self, file_name):
        self.AMSLogger.debug('In AbstractAMSMethod::_match_found_files(%s)' % file_name)
        self._matching_files_validated = True
        for pattern in self.config.file_patterns:
            self.AMSLogger.debug('Validating pattern=%s' % pattern)
            if self._regex_validator.validate(file_name, pattern):
                self.AMSLogger.info('filename={} matches pattern={}'.format(file_name, pattern))
                return True

            self.AMSLogger.warning('filename={} does *NOT* match pattern={}'.format(file_name, pattern))
        return False

    def _get_all_files_in_local_directory(self, directory):
        try:
            self.AMSLogger.info('Examining files in directory=%s' % directory)
            found_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            found_files_cnt = len(found_files)
            self.AMSLogger.info('Found %s files' % found_files_cnt)
            return found_files
        except OSError:
            raise AMSFatalException('From directory does not exist: %s' % directory)
        except Exception as e:
            raise AMSFatalException(e)

    def _success_handler(self, source_file, final_target):
        full_source_path = os.path.join(self.config.from_directory, source_file)
        if self.config.on_success_handler_script:
            self.AMSLogger.debug('Registered success handler=%s' % self.config.on_success_handler_script)
            try:
                ams_multi_thread = AMSMultiThread(self.AMSConfig, max_workers=self.AMSConfig.multi_thread_max_workers, timer_interval=self.AMSConfig.multi_thread_timer_check_interval)
                ams_multi_thread.run_job(self.config.on_success_handler_script, None, self.config.file_route_name, ['-s', full_source_path, '-d', final_target], callback_method=self._complete_handler)
            except Exception as e:
                self.AMSLogger.error('Failed to complete multi-threaded success handler: %s' % str(e))

    def _complete_handler(self, ams_return_code):
        """
        :param ams_return_code:
        :type ams_return_code: AMSScriptReturnCode
        :return:
        :rtype:
        """
        if ams_return_code.is_error():
            self.AMSLogger.error('On Success Handler script failed[%s]: %s' % (ams_return_code.script_name, ams_return_code.format_errors()))
            if self.jibbix_options:
                jira_summary = self.config.file_route_name + ' Rote | Failed on success handler %s' % ams_return_code.script_name
                jira_description = 'Script Name: %s\n' % ams_return_code.script_name
                jira_description += 'Error: %s' % ams_return_code.format_errors()
                self.event_handler.create(self.jibbix_options, summary=jira_summary, description=jira_description)
        else:
            self.AMSLogger.info('Complete handler finished successfully: %s' % ams_return_code.script_name)

    def _get_tmp_path(self, to_tmp_folder, source_file):
        return os.path.join(to_tmp_folder, source_file)

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name
