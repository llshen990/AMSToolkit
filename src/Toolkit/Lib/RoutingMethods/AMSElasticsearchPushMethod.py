import os
import sys
import shutil
import json
from elasticsearch import Elasticsearch

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.RoutingMethods import AbstractAMSMethod
from Toolkit.Exceptions import AMSMethodException, AMSFatalException


class AMSElasticsearchPushMethod(AbstractAMSMethod):
    def __init__(self, ams_config, config, jibbix_options):
        AbstractAMSMethod.__init__(self, ams_config, config, jibbix_options)
        host = self.config.host
        port = self.config.port
        if not host:
            host = 'localhost'
        if not port:
            port = 9200
        self.ams_esclient = Elasticsearch([{'host':host,'port':port}], send_get_body_as='POST')

    def _get_file_list(self):
        # This routing method pushes files from the local directory
        self._found_files = self._get_all_files_in_local_directory(self.config.from_directory)
        if len(self._found_files) > 0:
            return True
        return False

    def _check_and_create_target_to_dir(self):
        # maybe create the index?
        return True

    def _check_and_create_target_tmp_dir(self):
        try:
            self.AMSLogger.debug('In _check_and_create_target_tmp_dir().  Dir=%s' % self._to_tmp_folder)
            return self._method_make_dir(self._to_tmp_folder)
        except Exception as e:
            raise AMSMethodException(e)

    def _check_remote_final_target(self, final_target):
        # check to see if the index exists or always return false because each new post is really a new document
        return False

    def _route_tmp(self, source_file, to_path_tmp):
        try:
            self.AMSLogger.debug('Copying file=%s to tmp folder=%s' % (source_file, to_path_tmp))
            shutil.copy(os.path.join(self.config.from_directory, source_file), to_path_tmp)
            return True
        except Exception as e:
            raise AMSMethodException(e)

    def _route_final(self, source_file, final_target, to_path_tmp):
        try:
            # slurp from to_path_tmp into json object
            final_target = self.config.to_directory.lower()
            self.AMSLogger.debug('Posting file from tmp folder=%s to final index=%s' % (to_path_tmp, final_target))
            with open(to_path_tmp) as json_file:
                body = json.load(json_file)
                result = self.ams_esclient.index(index=final_target, body=body)
                # check that result is 'created'
                if result and 'result' in result:
                    return result['result'] is 'created'
                else:
                    return False
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
