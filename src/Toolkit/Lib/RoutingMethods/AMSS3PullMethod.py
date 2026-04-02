import os
import sys
import shutil

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.RoutingMethods import AbstractAMSMethod
from Toolkit.Lib.Helpers import AMSS3
from Toolkit.Exceptions import AMSMethodException, AMSFatalException
from Toolkit.Config import AMSFileRouteMethod


class AMSS3PullMethod(AbstractAMSMethod):
    def __init__(self, ams_config, config, jibbix_options):
        """
        :type config: AMSFileRouteMethod
        """
        AbstractAMSMethod.__init__(self, ams_config, config, jibbix_options)
        self.ams_s3 = AMSS3(config.s3_default_bucket, config.to_executable)

    def _get_file_list(self):
        try:
            self.AMSLogger.debug('In _get_file_list()')
            self._found_files = self.ams_s3.listdir(self.config.from_directory) #returns list of files
            file_count = len(self._found_files)
            self.AMSLogger.debug('Found {} files in {}'.format(file_count, self.config.from_directory))
            return True if file_count > 0 else False
        except Exception as e:
            raise AMSMethodException(e)

    def _route_tmp(self, source_file, to_path_tmp):
        try:
            self.AMSLogger.debug('Getting file: {} to tmp_dir: {}'.format(source_file, to_path_tmp))
            self.ams_s3.get(source_file, to_path_tmp)
            return True
        except Exception as e:
            raise AMSMethodException(e)

    def _route_final(self, source_file, final_target, to_path_tmp):
        try:
            self.AMSLogger.debug('Moving file from tmp_dir: {} to final location: {}'.format(to_path_tmp, os.path.join(self.config.to_directory, os.path.basename(final_target))))
            shutil.copy(to_path_tmp, os.path.join(self.config.to_directory, os.path.basename(final_target)))
            return True
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
            self.AMSLogger.debug('Removing source file: {}'.format(source_file))
            self.ams_s3.remove_file(source_file)
        except Exception as e:
            self.AMSLogger.critical('Could not remove source file: {} with error: {}'.format(source_file, str(e)))
            raise AMSFatalException(e)

    def _check_modified_time(self, file_path):
        try:
            self.AMSLogger.debug('Checking modified time for {}'.format(os.path.basename(file_path)))
            return self.ams_s3.check_modified()
        except Exception as e:
            self.AMSLogger.critical('Could not find modified time for file: {} with error: {}'.format(file_path, str(e)))

    def _get_tmp_path(self, to_tmp_folder, source_file):
        return os.path.join(to_tmp_folder, os.path.basename(os.path.join(to_tmp_folder, source_file)))