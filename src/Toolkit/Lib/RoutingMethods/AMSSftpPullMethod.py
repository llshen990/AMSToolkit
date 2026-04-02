import os
import sys
import shutil

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.RoutingMethods import AbstractAMSMethod
from Toolkit.Lib.Helpers import AMSSftp
from Toolkit.Exceptions import AMSMethodException, AMSFatalException, AMSSftpException
from Toolkit.Config import AMSFileRouteMethod

class AMSSftpPullMethod(AbstractAMSMethod):
    def __init__(self, ams_config, config, jibbix_options):
        """
        :type config: AMSFileRouteMethod
        """
        AbstractAMSMethod.__init__(self, ams_config, config, jibbix_options)
        self.ams_sftp = AMSSftp(config.decrypt(config.username), config.host, config.port, config.decrypt(config.password), config.key_file)

    def _get_file_list(self):
        try:
            self.AMSLogger.debug('In _get_file_list()')
            self._found_files = self.ams_sftp.listdir(self.config.from_directory)
            found_files_cnt = len(self._found_files)
            self.AMSLogger.debug('Found %s files in %s' % (found_files_cnt, self.config.from_directory))
            if found_files_cnt > 0:
                return True
            return False
        except IOError:
            self.AMSLogger.info('username=%s|host=%s|port=%s' % (self.config.username, self.config.host, self.config.port))
            raise AMSMethodException('From directory does not exist remotely: %s' % self.config.from_directory)
        except Exception as e:
            raise AMSMethodException(e)

    def _route_tmp(self, source_file, to_path_tmp):
        try:
            self.AMSLogger.debug('Getting file=%s to tmp folder=%s' % (source_file, to_path_tmp))
            self.ams_sftp.get(os.path.join(self.config.from_directory, source_file), to_path_tmp)
            return True

        except AMSFatalException:
            raise
        except Exception as e:
            raise AMSMethodException(e)

    def _route_final(self, source_file, final_target, to_path_tmp):
        try:
            self.AMSLogger.debug('Moving file from tmp folder=%s to final destination=%s' % (to_path_tmp, final_target))
            shutil.copy(to_path_tmp, final_target)
            return True
        except AMSFatalException:
            raise
        except Exception as e:
            raise AMSMethodException(e)

    def _check_and_create_target_to_dir(self):
        try:
            self.AMSLogger.debug('In _check_and_create_target_to_dir().  Dir=%s' % self.config.to_directory)
            return self._method_make_dir(self.config.to_directory)
        except Exception as e:
            raise AMSMethodException(e)

    def _check_and_create_target_tmp_dir(self):
        try:
            self.AMSLogger.debug('In _check_and_create_target_tmp_dir().  Dir=%s' % self._to_tmp_folder)
            return self._method_make_dir(self._to_tmp_folder)
        except Exception as e:
            raise AMSMethodException(e)

    def _check_remote_final_target(self, final_target):
        try:
            self.AMSLogger.debug('In _check_remote_final_target(%s)' % final_target)
            return os.path.exists(final_target)
        except IOError:
            return False
        except Exception as e:
            raise AMSFatalException(e)

    def _remove_source_file(self, source_file):
        try:
            abs_path_source_file = os.path.abspath(os.path.join(self.config.from_directory, source_file))
            self.AMSLogger.info('username=%s|host=%s|port=%s' % (self.config.username, self.config.host, self.config.port))
            self.AMSLogger.debug('Removing source file=%s.' % abs_path_source_file)
            self.ams_sftp.remove_file(abs_path_source_file)
        except AMSSftpException:
            raise
        except Exception as e:
            self.AMSLogger.critical('Could not remove source file=%s with error=%s' % (source_file, str(e)))
            raise AMSFatalException(e)

    def _check_modified_time(self, file_path):
        try:
            self.AMSLogger.debug('Checking modified time for {})'.format(file_path))
            return self.ams_sftp.check_modified(file_path)
        except Exception as e:
            self.AMSLogger.critical('Could not find modified time for file: {} with error: {}'.format((file_path), str(e)))

    # def _route(self):
    #     # @todo: add in validations
    #     try:
    #         self.AMSLogger.debug('In route source, attempting to get %s files from Sftp' % len(self._matching_files))
    #         for source_file in self._matching_files:
    #             self.AMSLogger.debug('Getting file %s' % source_file)
    #             self.ams_sftp.get(source_file, self._to_tmp_folder)
    #             self.ams_sftp.rename(self._to_tmp_folder + '/' + source_file, self.config.to_directory)
    #     except Exception as e:
    #         raise AMSMethodException(e)