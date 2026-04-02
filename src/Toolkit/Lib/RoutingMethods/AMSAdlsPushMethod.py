import os
import sys
import shutil

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.RoutingMethods import AbstractAMSMethod
from Toolkit.Lib.Helpers import AMSADLS
from Toolkit.Exceptions import AMSMethodException, AMSFatalException, AMSADLSException
from Toolkit.Config import AMSFileRouteMethod


class AMSADLSPushMethod(AbstractAMSMethod):
    def __init__(self, ams_config, config, jibbix_options):
        """
        :type config: AMSFileRouteMethod
        """
        AbstractAMSMethod.__init__(self, ams_config, config, jibbix_options)
        self.ams_adls = AMSADLS(config.tenant, config.client_id, config.decrypt(config.client_secret), config.store_name)

    def _get_file_list(self):
        try:
            self._found_files = self._get_all_files_in_local_directory(self.config.from_directory)
            file_count = len(self._found_files)
            self.AMSLogger.debug('Found {} files in {}'.format(file_count, self.config.from_directory))
            return True if file_count > 0 else False
        except Exception as e:
            raise AMSMethodException(e)

    def _route_tmp(self, source_file, to_path_tmp):
        try:
            self.AMSLogger.debug('Pushing file: {} to tmp folder: {}'.format(source_file, to_path_tmp))
            self.ams_adls.put(os.path.join(self.config.from_directory, source_file), to_path_tmp)
            return True
        except AMSFatalException:
            raise
        except Exception as e:
            raise AMSMethodException(e)

    def _route_final(self, source_file, final_target, to_path_tmp):
        try:
            self.AMSLogger.debug('Moving file from tmp folder: {} to final dest: {}'.format(to_path_tmp, final_target))
            self.ams_adls.rename(to_path_tmp, final_target)
        except AMSFatalException:
            raise
        except AMSMethodException as e:
            raise AMSMethodException(e)

    def _check_remote_final_target(self, final_target):
        try:
            self.AMSLogger.debug('Checking remote for: {}'.format(final_target))
            self.ams_adls.stat(final_target)
            return None
        except Exception as e:
            raise AMSFatalException(e)

    def _check_and_create_target_tmp_dir(self):
        try:
            self.AMSLogger.debug('Creating tmp dir on remote: {}'.format(self._to_tmp_folder))
            return self.ams_adls.create_dir(self._to_tmp_folder)
        except Exception as e:
            raise AMSMethodException(e)

    def _check_and_create_target_to_dir(self):
        try:
            self.AMSLogger.debug('Creating target dir on remote: {}'.format(self.config.to_directory))
            return self.ams_adls.create_dir(self.config.to_directory)
        except Exception as e:
            raise AMSMethodException(e)

    def _check_remote_dir(self, directory):
        try:
            self.AMSLogger.debug('Checking remote dir: {}'.format(directory))
            self.ams_adls.listdir(directory)
            return True
        except Exception as e:
            raise AMSMethodException(e)

    def _create_remote_dir(self, directory):
        try:
            self.AMSLogger.debug('Creating remote dir: {}'.format(directory))
            self.ams_adls.create_dir(directory)
        except Exception as e:
            self.AMSLogger.critical('Could not create remote dir: {}'.format(directory))
            raise AMSFatalException(e)

    def _remove_source_file(self, source_file):
        try:
            abs_path_source_file = os.path.abspath(os.path.join(self.config.from_directory, source_file))
            self.AMSLogger.debug('Removing source file: {}'.format(abs_path_source_file))
            os.remove(abs_path_source_file)
        except Exception as e:
            self.AMSLogger.critical('Could not remove source file: {} with error: {}'.format(source_file, str(e)))
            raise AMSFatalException(e)

    def _check_modified_time(self, file_path):
        try:
            self.AMSLogger.debug('Checking modified time for {}'.format(file_path))
            return int(os.stat(file_path).st_mtime)
        except Exception as e:
            self.AMSLogger.critical('Could not find modified time for file: {} with error: {}'.format(file_path, str(e)))

