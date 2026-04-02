import os
import subprocess
import sys
import boto3
import logging

from Toolkit.Exceptions import AMSS3Exception

class AMSS3(object):

    def __init__(self, default_bucket, to_executable):

        self.default_bucket = default_bucket

        self.logger = logging.getLogger('AMS')
        self.logger.info('Running executable to generate temporary credentials with path {}'.format(to_executable))

        # TODO: Check this return value and do something if it fails
        self.logger.info("Return value is: {}".format(subprocess.check_output([to_executable], shell=True)))

        self.logger.info('Successfully generated temporary credentials for job')
        self.logger.info('Attempting Authentication with S3')
        self.s3_client = boto3.client('s3')
        self.logger.info('Getting Session Object')
        self.s3_session = boto3.session.Session()
        self.logger.info('Getting Resource Object')
        self.s3_resource = self.s3_session.resource('s3')
        self.logger.info('S3 Authentication successful')
        self.logger.info('Initializing S3 connection.')

    def put(self, local_path, remote_path, bucket_name=None):
        """
        Pushes files from path {local_path} to path {remote_path}
        :param local_path:
        :param remote_path:
        :param bucket_name:
        :return: none
        """
        try:
            if not bucket_name:
                self.logger.debug('Using default bucket={}'.format(self.default_bucket))
                bucket_name = self.default_bucket
            if remote_path[0] == '/':
                self.logger.debug('Stripping leading / from remote_path={}'.format(remote_path))
                remote_path = remote_path[1:]
            self.logger.info('Putting file from local_path={} to remote_path={} bucket_name={}'.format(local_path, remote_path, bucket_name))
            return self.s3_client.upload_file(Filename=local_path, Bucket=bucket_name, Key=remote_path)
        except Exception as e:
            self.logger.critical('Failed to upload_file local_path={} to remote_path={}:'.format(local_path, remote_path))
            raise AMSS3Exception(e)

    def get(self, remote_path, local_path, bucket_name=None):
        """
        pulls from remote_path and downloads to local_path
        :param remote_path:
        :param local_path:
        :param bucket_name:
        :return:
        """
        try:
            if not bucket_name:
                self.logger.debug('Using default bucket={}'.format(self.default_bucket))
                bucket_name = self.default_bucket
            if remote_path[0] == '/':
                self.logger.debug('Stripping leading / from remote_path={}'.format(remote_path))
                remote_path = remote_path[1:]
            self.logger.info('Getting file from remote_path={} to local_path={} bucket_name={}'.format(remote_path, local_path, bucket_name))
            return self.s3_client.download_file(Bucket=bucket_name, Key=remote_path, Filename=local_path)
        except Exception as e:
            self.logger.critical('Failed to download_file remote_path={} -> local_path={} for reason={}'.format(remote_path, local_path, str(e)))
            raise AMSS3Exception(e)

    def listdir(self, directory, bucket_name=None):
        try:
            if not bucket_name:
                self.logger.debug('Using default bucket={}'.format(self.default_bucket))
                bucket_name = self.default_bucket
            if directory[0] == '/':
                self.logger.debug('Stripping leading / from directory={}'.format(directory))
                directory = directory[1:]
            end = '' if directory[-1] == '/' else '/'
            directory+=end
            bucket = self.s3_resource.Bucket(bucket_name)
            self.logger.info('Invoking listdir for destination_dir={} bucket_name={}'.format(directory, bucket_name))
            return [s3_file.key for s3_file in bucket.objects.filter(Prefix=directory)]
        except Exception as e:
            self.logger.critical('Failed to listdir directory={} for reason={}'.format(directory, str(e)))
            raise AMSS3Exception(e)

    def create_dir(self, directory, bucket_name=None):
        try:
            if not bucket_name:
                self.logger.debug('Using default bucket={}'.format(self.default_bucket))
                bucket_name=self.default_bucket
            # the directory name cannot start with a forward slash and must end in a forward slash
            directory = update_path(directory)
            self.logger.info('Generating directory in S3 directory={} bucket_name={}'.format(directory, bucket_name))
            return self.s3_client.put_object(Bucket=bucket_name, Key=directory)
        except Exception as e:
            self.logger.critical('Failed to create_dir directory={} for reason={}'.format(directory, str(e)))
            raise AMSS3Exception(e)

    def create_bucket(self, bucket_name, region):
        """
        :param bucket_name: name of remote bucket
        :param region: 'EU'|'eu-west-1'|'us-west-1'|'us-west-2'|'ap-south-1'|'ap-southeast-1'|'ap-southeast-2'|'ap-northeast-1'|'sa-east-1'|'cn-north-1'|'eu-central-1'
        :return: none
        """
        try:
            self.logger.info('Trying to create remote bucket_name={} region={}'.format(bucket_name, region))
            return self.s3_client.create_bucket(Bucket=bucket_name,
                                                CreateBucketConfiguration={'LocationConstraint': region})
        except Exception as e:
            self.logger.critical('Failed to create bucket bucket_name={} region={} for reason={}'.format(bucket_name, region, str(e)))
            raise AMSS3Exception(e)

    def rename(self, current_path, new_path, bucket_name=None):
        try:
            if not bucket_name:
                self.logger.debug('Using default bucket={}'.format(self.default_bucket))
                bucket_name=self.default_bucket
            if new_path[0] == '/':
                self.logger.debug('Stripping leading / from new_path={}'.format(new_path))
                new_path = new_path[1:]
            # copy_object needs fully qualified source name with buket_name and path
            self.logger.info('Renaming (moving) from current_path={} to newpath={} bucket_name={}'.format(current_path, new_path, bucket_name))
            self.s3_client.copy(Bucket=bucket_name, CopySource={'Bucket': bucket_name, 'Key': current_path}, Key=new_path)
            if current_path[0] == '/':
                self.logger.debug('Stripping leading / from current_path={}'.format(current_path))
                current_path = current_path[1:]
            return self.s3_client.delete_object(Bucket=bucket_name, Key=current_path)
        except Exception as e:
            self.logger.critical('Failed to rename current_path={} new_path={} for reason={}'.format(current_path, new_path, str(e)))
            raise AMSS3Exception(e)

    def stat(self, file_name, bucket_name=None):
        try:
            if not bucket_name:
                self.logger.debug('Using default bucket={}'.format(self.default_bucket))
                bucket_name = self.default_bucket
            self.logger.info('Verifying existence of file_name={} bucket_name={}'.format(file_name, bucket_name))
            # head_object retrieves metadata so if there is an exception we know the path doesn't exist in the bucket
            return self.s3_client.head_object(Bucket=bucket_name, Key=file_name)
        except Exception as e:
            # Not sure why we ignore this exception
            self.logger.critical('Failed to stat (ignoring?) file_name={} for reason={}'.format(file_name, str(e)))
        return None

    def remove_file(self, file_name, bucket_name=None):
        """
        removes file {file_name} from bucket {bucket_name}
        :param file_name: name of file which is to be deleted
        :param bucket_name:
        :return: none
        """
        try:
            if not bucket_name:
                self.logger.debug('Using default bucket={}'.format(self.default_bucket))
                bucket_name = self.default_bucket
            self.logger.info('Trying to remove file_name={} bucket_name={}'.format(file_name, bucket_name))
            return self.s3_client.delete_object(Bucket=bucket_name, Key=file_name)
        except Exception as e:
            self.logger.critical('Failed to remove_file file_name={} for reason={}'.format(file_name, str(e)))
            raise AMSS3Exception(e)

    def exists(self, path, bucket_name=None):
        try:
            if not bucket_name:
                self.logger.debug('Using default bucket={}'.format(self.default_bucket))
                bucket_name=self.default_bucket
            self.logger.info('Verifying existence of path={} bucket_name={}'.format(path, bucket_name))
            bucket = self.s3_resource.Bucket(bucket_name)
            end = '' if path[-1] == '/' else '/'
            return len(bucket.objects.filter(Prefix=(path + end))) == 0
        except Exception as e:
            self.logger.critical('Failed to check exists path={} for reason={}'.format(path, str(e)))
            raise AMSS3Exception(e)

    def check_modified(self):
        try:
            # Couldn't we do a check_modified looking at versions?
            self.logger.info('S3 has eventual consistency. Check modified returns 0')
            return 0
        except Exception as e:
            raise AMSS3Exception(e)

    def get_dir(self, remote_path, local_path, bucket_name=None):
        """
        pulls from remote_path and downloads to local_path
        :param remote_path:
        :param local_path:
        :param bucket_name:
        :return:
        """
        try:
            if not bucket_name:
                self.logger.debug('Using default bucket={}'.format(self.default_bucket))
                bucket_name = self.default_bucket
            self.logger.info('Getting file from remote remote_path={} to local_path={} bucket_name={}'.format(remote_path, local_path, bucket_name))
            bucket = self.s3_resource('s3').Bucket(bucket_name)
            for myObject in bucket.objects.filter(Prefix=remote_path):
                if not os.path.exists(os.path.dirname(myObject.key)):
                    os.makedirs(os.path.dirname(myObject.key))
                bucket.download_file(Bucket=bucket_name, Key=myObject.key, FileName=local_path)
        except Exception as e:
            self.logger.critical('Failed to download remote_path={} -> local_path={} for reason={}'.format(remote_path, local_path, str(e)))
            raise AMSS3Exception(e)

    #noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name

def update_path(path):
    #S3 prefixes take on specific formatting: 1) must NOT start with slash 2) must end with slash
    if path[0] == '/': path = path[1:]
    end = '' if path[-1] == '/' else '/'
    return path + end
