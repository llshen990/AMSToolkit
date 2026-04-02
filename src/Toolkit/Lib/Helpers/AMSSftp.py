import os
import paramiko
import sys
import logging

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))

from Toolkit.Exceptions import AMSSftpException

class AMSSftp(object):
    DEFAULT_SSH_PORT = 22

    def __init__(self, username, host, port=None, password=None, key_file=None):
        # @todo: add validations
        self.username = username
        self.port = port
        self.password = password
        self.key_file = key_file
        self.host = host
        self.logger = logging.getLogger('AMS')

        self.client = paramiko.SSHClient()

        # add ssh-rsa key if configured
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        if not self.port:
            self.port = AMSSftp.DEFAULT_SSH_PORT

        self.logger.info('Trying to connect to SFTP server.  User=%s, Host=%s, Port=%s' % (self.username, self.host, self.port))
        if self.key_file not in [None, '', 'None']:
            self.logger.debug('Using ssh-rsa key from key_file=' + str(self.key_file))
            if self.password is None or self.key_file is '':
                key = paramiko.RSAKey.from_private_key_file(self.key_file)
            else:
                key = paramiko.RSAKey.from_private_key_file(self.key_file, self.password)

            self.client.get_host_keys().add(self.host, 'ssh-rsa', key)
            self.client.connect(self.host, port=self.port, username=self.username, pkey=key)
        else:
            self.client.connect(self.host, port=self.port, username=self.username, password=self.password, look_for_keys=False)

        self.logger.debug('Client connection to SFTP server successful')

        self.sftp = self.client.open_sftp()  # type: paramiko.SFTPClient

        self.logger.debug('client.open_sftp() successful')

    def put(self, local_path, remote_path):
        """

        :param local_path:
        :type local_path:
        :param remote_path:
        :type remote_path:
        :return:
        :rtype: paramiko.SFTPAttributes
        """
        try:
            self.logger.info('Putting file from local_path=%s to remote_path=%s' % (local_path, remote_path))
            return self.sftp.put(local_path, remote_path)  # type: paramiko.SFTPAttributes
        except Exception as e:
            self.logger.critical('Failed to upload local_path=%s -> remote_path=%s for reason=%s' % (local_path, remote_path, str(e)))
            raise AMSSftpException(e)

    def get(self, remote_path, local_path):
        try:
            self.logger.info('Getting file from remote_path=%s to local_path=%s' % (remote_path, local_path))
            self.sftp.get(remote_path, local_path)
        except Exception as e:
            raise AMSSftpException(e)

    def listdir(self, directory):
        try:
            self.logger.info('Invoking listdir for destination_dir=%s' % directory)
            return self.sftp.listdir(directory)
        except IOError:
            raise
        except Exception as e:
            raise AMSSftpException(e)

    def create_dir(self, directory):
        try:
            self.logger.info('Trying to create remote directory=%s' % directory)
            return self.sftp.mkdir(directory)
        except IOError:
            raise
        except Exception as e:
            raise AMSSftpException(e)

    def rename(self, current_path, new_path):
        try:
            self.logger.info('Renaming (moving) from=%s to %s' % (current_path, new_path))
            return self.sftp.rename(current_path, new_path)
        except Exception as e:
            raise AMSSftpException(e)

    def stat(self, file_name):
        """

        :param file_name:
        :type file_name:
        :return:
        :rtype: paramiko.SFTPAttributes
        """
        try:
            self.logger.info('Getting stat (checking if file exists) for file_name=%s' % file_name)
            return self.sftp.stat(file_name)
        except IOError:
            raise
        except Exception as e:
            raise AMSSftpException(e)

    def check_and_create_dir(self, directory):
        try:
            self.logger.info('Checking to see if directory=%s exists remotely' % directory)
            try:
                self.sftp.stat(directory)
            except IOError:
                self.logger.debug('directory=%s does not exist remotely, will attempt to create it' % directory)

            self.sftp.mkdir(directory)
            return True
        except Exception as e:
            raise AMSSftpException(e)

    def remove_file(self, file_name):
        try:
            self.logger.info('Trying to remove file=%s' % file_name)
            try:
                self.sftp.remove(file_name)
                return True
            except IOError as e:
                self.logger.debug('file=%s does not exist remotely or we do not have permissions to remove' % file_name)
                raise AMSSftpException(e)
        except Exception as e:
            raise AMSSftpException(e)

    def close(self):
        try:
            if hasattr(self, 'logger') and hasattr(self, 'client'):
                self.logger.debug('Closing connection to host=%s with username=%s' % (self.host, self.username))
            if hasattr(self, 'client'):
                self.client.close()
        except Exception as e:
            raise AMSSftpException(e)

    def check_modified(self, file_path):
        try:
            self.logger.debug('Checking modified time of file: {}'.format(file_path))
            return int(self.sftp.stat(file_path).st_mtime)
        except Exception as e:
            raise AMSSftpException(e)

    def __del__(self):
        self.close()

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name