import os
import sys
import shutil

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.RoutingMethods import AbstractAMSMethod
from Toolkit.Exceptions import AMSMethodException, AMSFatalException

class AMSMoveMethod(AbstractAMSMethod):
    def __init__(self, ams_config, config, jibbix_options):
        AbstractAMSMethod.__init__(self, ams_config, config, jibbix_options)

    def _get_file_list(self):
        self._found_files = self._get_all_files_in_local_directory(self.config.from_directory)
        if len(self._found_files) > 0:
            return True
        return False

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

    def _route_tmp(self, source_file, to_path_tmp):
        try:
            self.AMSLogger.debug('Copying file=%s to tmp folder=%s' % (source_file, to_path_tmp))
            shutil.copy(os.path.join(self.config.from_directory, source_file), to_path_tmp)
            return True
        except Exception as e:
            raise AMSMethodException(e)

    def _route_final(self, source_file, final_target, to_path_tmp):
        try:
            self.AMSLogger.debug('Moving file from tmp folder=%s to final destination=%s' % (to_path_tmp, final_target))
            shutil.move(to_path_tmp, final_target)
            return True
        except AMSFatalException:
            raise
        except Exception as e:
            raise AMSMethodException(e)

    def _remove_source_file(self, source_file):
        try:
            abs_path_source_file = os.path.abspath(os.path.join(self.config.from_directory, source_file))
            self.AMSLogger.debug('Removing source file=%s.' % abs_path_source_file)
            os.remove(abs_path_source_file)
        except Exception as e:
            self.AMSLogger.critical('Could not remove source file=%s with error=%s' % (source_file, str(e)))
            raise AMSFatalException(e)

    def _check_modified_time(self, filename):
        try:
            self.AMSLogger.debug('Checking modification time of: {}'.format(filename))
            return int(os.stat(filename).st_mtime)
        except Exception as e:
            raise AMSMethodException(e)
