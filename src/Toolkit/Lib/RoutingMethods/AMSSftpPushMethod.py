import os
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.RoutingMethods import AbstractAMSMethod
from Toolkit.Lib.Helpers import AMSSftp
from Toolkit.Exceptions import AMSMethodException, AMSFatalException
from Toolkit.Config import AMSFileRouteMethod

class AMSSftpPushMethod(AbstractAMSMethod):
    def __init__(self, ams_config, config, jibbix_options):
        """
        :type config: AMSFileRouteMethod
        """
        AbstractAMSMethod.__init__(self, ams_config, config, jibbix_options)
        self.ams_sftp = AMSSftp(config.decrypt(config.username), config.host, config.port, config.decrypt(config.password), config.key_file)

    def _get_file_list(self):
        self._found_files = self._get_all_files_in_local_directory(self.config.from_directory)
        if len(self._found_files) > 0:
            return True
        return False

    def _route_tmp(self, source_file, to_path_tmp):
        try:
            self.AMSLogger.debug('Putting file=%s to tmp folder=%s' % (source_file, to_path_tmp))
            self.ams_sftp.put(os.path.join(self.config.from_directory, source_file), to_path_tmp)
            return True

        except AMSFatalException:
            raise
        except Exception as e:
            raise AMSMethodException(e)

    def _route_final(self, source_file, final_target, to_path_tmp):
        try:
            self.AMSLogger.debug('Moving remote file from tmp folder=%s to final destination=%s' % (to_path_tmp, final_target))
            self.ams_sftp.rename(to_path_tmp, final_target)
            return True
        except AMSFatalException:
            raise
        except Exception as e:
            raise AMSMethodException(e)

    def _check_remote_final_target(self, final_target):
        try:
            self.AMSLogger.debug('In _check_remote_final_target(%s)' % final_target)
            return self.ams_sftp.stat(final_target)
        except IOError:
            return False
        except Exception as e:
            raise AMSFatalException(e)

    def _check_and_create_target_tmp_dir(self):
        try:
            self.AMSLogger.debug('In _check_and_create_target_tmp_dir().  Dir=%s' % self._to_tmp_folder)
            return self._check_remote_dir(self._to_tmp_folder)
        except AMSFatalException:
            raise
        except Exception as e:
            raise AMSMethodException(e)

    def _check_and_create_target_to_dir(self):
        try:
            self.AMSLogger.debug('In _check_and_create_target_to_dir().  Dir=%s' % self.config.to_directory)
            return self._check_remote_dir(self.config.to_directory)
        except AMSFatalException:
            raise
        except Exception as e:
            raise AMSMethodException(e)

    def _check_remote_dir(self, directory, create=True):
        try:
            self.AMSLogger.debug('In _check_remote_dir(%s)' % directory)
            self.ams_sftp.listdir(directory)
            return True
        except IOError:
            if create:
                return self._create_remote_dir(directory)
        except Exception as e:
            raise AMSMethodException(e)

    def _create_remote_dir(self, directory):
        try:
            self.AMSLogger.info('username=%s|host=%s|port=%s' % (self.config.username, self.config.host, self.config.port))
            self.AMSLogger.debug('%s directory does not exist remotely.' % directory)
            self.ams_sftp.create_dir(directory)
            return True
        except Exception as e:
            self.AMSLogger.critical('Could not create remote directory directory=%s with error=%s' % (directory, str(e)))
            raise AMSFatalException(e)

    def _remove_source_file(self, source_file):
        try:
            abs_path_source_file = os.path.abspath(os.path.join(self.config.from_directory, source_file))
            self.AMSLogger.debug('Removing source file=%s.' % abs_path_source_file)
            os.remove(abs_path_source_file)
        except Exception as e:
            self.AMSLogger.critical('Could not remove source file=%s with error=%s' % (source_file, str(e)))
            raise AMSFatalException(e)

    def _check_modified_time(self, file_path):
        try:
            self.AMSLogger.debug('Checking modified time for {}'.format(file_path))
            return int(os.stat(file_path).st_mtime)
        except Exception as e:
            self.AMSLogger.critical('Could not find modified time for file: {}'.format(file_path) + str(e))

