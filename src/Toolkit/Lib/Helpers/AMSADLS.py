import os
import sys
import logging
from azure.datalake.store import core, lib, exceptions

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))

from Toolkit.Exceptions import AMSADLSException


class AMSADLS(object):

    def __init__(self, tenant, client_id, client_secret, store_name):
        self.tenant = tenant
        self.client_id = client_id
        self.client_secret = client_secret
        self.store_name = store_name
        self.logger = logging.getLogger('AMS')

        self.logger.info('Attempting authentication with data lake.')
        self.adlsCreds = lib.auth(tenant_id=self.tenant,
                                  client_id=self.client_id,
                                  client_secret=self.client_secret)
        self.logger.info('Data lake authentication successful.')
        self.client = core.AzureDLFileSystem(self.adlsCreds, store_name=self.store_name)
        self.logger.info('Initializing ADLS connection.')


    def put(self, local_path, remote_path):
        try:
            self.logger.info('Putting file from local path: {} to remote path: {}'.format(local_path, remote_path))
            return self.client.put(local_path, remote_path)
        except Exception as e:
            self.logger.critical('Failed to upload local path: {} to remote path {}:'.format(local_path, remote_path))
            raise AMSADLSException(e)


    def get(self, remote_path, local_path):
        try:
            self.logger.info('Getting file from remote path: {} to local path: {}'.format(remote_path, local_path))
            self.client.get(remote_path, local_path)
        except Exception as e:
            raise AMSADLSException(e)


    def listdir(self, directory):
        try:
            self.logger.info('Invoking listdir for destination: {}'.format(directory))
            return [os.path.basename(adls_file) for adls_file in self.client.ls(directory, invalidate_cache=True)]
        except Exception as e:
            raise AMSADLSException(e)


    def create_dir(self, directory):
        # Current behavior of mkdir on adls does not overwrite existing directory
        try:
            self.logger.info('Trying to create remote directory: {}'.format(directory))
            self.client.mkdir(directory)
        except Exception as e:
            raise AMSADLSException(e)
        return True


    def rename(self, current_path, new_path):
        try:
            self.logger.info('Renaming (moving) from {} to {}.'.format(current_path, new_path))
            return self.client.mv(current_path, new_path)
        except Exception as e:
            raise AMSADLSException(e)


    def stat(self, file_name):
        try:
            self.logger.info('Getting stat for file: {}'.format(file_name))
            return self.client.info(file_name, invalidate_cache=True)
        except exceptions.FileNotFoundError:
            return None
        except Exception as e:
            raise AMSADLSException(e)


    def remove_file(self, file_name):
        try:
            self.logger.info('Trying to remove file: {}'.format(file_name))
            try:
                self.client.rm(file_name)
                return True
            except exceptions.FileNotFoundError as e:
                self.logger.debug('File: {} does not exist on remote.'.format(file_name))
                raise AMSADLSException(e)
        except Exception as e:
            raise AMSADLSException(e)


    def remove_dir(self, dir_name):
        try:
            self.logger.info('Trying to remove directory: {}'.format(dir_name))
            try:
                self.client.rmdir(dir_name)
                return True
            except exceptions.FileNotFoundError as e:
                self.logger.debug('Directory: {} does not exist on remote.'.format(dir_name))
                raise AMSADLSException(e)
        except Exception as e:
            raise AMSADLSException(e)


    def exists(self, path):
        try:
            self.logger.info('Verifying existence of path: {}'.format(path))
            return self.client.exists(path, invalidate_cache=True)
        except Exception as e:
            raise AMSADLSException(e)


    def check_modified(self, file_path):
        try:
            self.logger.info('Returning modified time of: {}'.format(file_path))
            resp = self.stat(file_path)
            if 'modificationTime' in resp.keys():
                return resp['modificationTime'] // 1000
            else:
                self.logger.debug('modificationTime not found in response for: {}'.format(file_path))
        except Exception as e:
            raise AMSADLSException(e)


    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name
