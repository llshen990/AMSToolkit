import os
import json
import shutil
import sys
from time import strftime

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from Toolkit.Exceptions import AMSFileAlertingException
from Toolkit.Config import AMSJibbixOptions, AMSAttributeMapper
from lib.Validators import FileExistsValidator

class AMSFileAlert(AbstractAMSBase):

    def __init__(self, ams_config, src_path, dest_path):
        AbstractAMSBase.__init__(self, ams_config)

        self.ams_attribute_mapper = AMSAttributeMapper()
        self.ams_jibbix_options = AMSJibbixOptions()
        self.AMSConfig = ams_config
        self.src_filename_path = src_path  # type: str
        self.dest_filename_path = dest_path  # type: str
        self.processed_path = os.path.join(os.path.dirname(dest_path), 'successfully-processed')
        self.hostname = None  # type: str
        self.tla = None  # type: str
        self._set_tla_and_hostname()
        self.schedule_name = self.tla
        self.fev = FileExistsValidator(True)
        # There should be base config file in /sso/sfw/ghusps-toolkit/config/rmss/{}.json, for this to work.
        self.base_jibbix = AMSJibbixOptions()
        self.AMSDefaults.my_hostname = self.hostname
        self.event_handler = self.ams_attribute_mapper.get_attribute('global_ams_event_handler')
        self.event_handler.zabbix.my_hostname = self.hostname
        self.override_str = ""
        self.allowed_jibbix_overrides = [
            'project',
            'priority',
            'security',
            'type',
            'link',
            'watchers',
            'component',
            'labels',
            'merge',
            'bundle',
            'bundle_time',
            'notify',
            'comm_status_prod',
            'comm_status_test',
            'comm_status_dev',
            'comm_status_env_4',
            'comm_status_env_5',
            'comm_status_env_6',
            'host',
            'comment_only',
            'summary',
            'comment',
            'schedule_name',
            'assignee'
        ]

    def check_destination_path(self):
        """
        Method to check if the dest file path exists
        :return: True if file exists, False if it doesn't
        """
        if not self.fev.validate(self.dest_filename_path):
            raise AMSFileAlertingException('Could not find file containing alerts: ' + self.fev.format_errors())

        return True

    def _set_tla_and_hostname(self):
        """
        Parsing tla and hostname of the dest_filename_path
        :return:
        """
        dest_file = self.dest_filename_path.split("/")[-1]
        self.tla = dest_file.split("_")[0].upper()
        self.hostname = dest_file.split("_")[1].lower()

        return True

    def _validate_if_tla_exists(self):
        """
        This Method is to check if config exists in a defined config path
        :return:
        """
        std_config_path = self.AMSDefaults.rmss_default_supplemental_jibbix_options.format(self.tla)
        if not self.fev.validate(std_config_path):
            err = "TLA json for {} does not exist in {}".format(self.tla, std_config_path)
            self.AMSLogger.info(err)
            return False
        else:
            self.AMSLogger.info("Tla is available in {} ".format(std_config_path))

            with open(std_config_path) as f:
                # loading base jibbix options from stg config file if exists
                tmp_jibbix_dict = json.load(f)
                self.base_jibbix.load(std_config_path, tmp_jibbix_dict['jibbix_options'])
            return True

    def _parse_json_object(self, json_file):
        """
        This Method wil parse json file and verify the instance of json
        :param :
        :return:
        """
        with open(json_file) as f:
            self.AMSLogger.info("Parsing json: {}".format(json_file))
            data = json.load(f)

        if isinstance(data, list):
            return True, data
        else:
            self.AMSLogger.critical("Invalid json file found:  {}".format(json_file))
            return False, []

    def load_to_jibbix(self):
        """
        This method calls other methods to parse json object,update jibbix_options and send alerts from AMSZabbixEvent handler
        :return:
        """
        status, result = self._parse_json_object(self.dest_filename_path)
        tmp_failed_issues = []
        self._validate_if_tla_exists()

        for data in result:
            try:
                if 'jibbix_options' not in data:
                    self.AMSLogger.debug('jibbix_options not in data element, moving on...')
                    continue

                if not data['jibbix_options']:
                    self.AMSLogger.debug('jibbix_options is empty in data element, moving on...')
                    continue

                self.update_jibbix_options(data["jibbix_options"])
                if not self.send_alerts_to_zabbix():
                    # build to send new file back to source for the events that haven't been processed.
                    tmp_failed_issues.append(data)
            except Exception as e:
                self.AMSLogger.critical("Caught exception processing alert for {}: {}".format(self.dest_filename_path, str(e)))
                self.AMSLogger.debug("Routing file back to source directory for retry.")
                try:
                    shutil.move(self.dest_filename_path, self.src_filename_path)
                except Exception as ex:
                    self.AMSLogger.warning("Caught exception when moving file {} to {} : {}".format(self.dest_filename_path, self.src_filename_path, str(ex)))

                raise e

        if tmp_failed_issues:
            # path = '/'.join(self.dest_filename_path.split('/')[:-1])
            source_without_extension = os.path.splitext(self.src_filename_path)[0]
            source_folder = os.path.dirname(os.path.abspath(self.src_filename_path))
            reprocess_file_name = source_without_extension + '_' + strftime('%Y%m%d_%H%M%S') + '.json'
            with open(os.path.join(source_folder, reprocess_file_name), 'w') as f:
                json.dump(tmp_failed_issues, f)

        self._move_to_processed()

        return True

    def update_jibbix_options(self, options):
        """
        This method is to update existing jibbix options that calls load method, supplement info from base_jibbix options if missing  from AMSJibbixOptions
        :return: jibbix_options that are converted to string.
        :rtype: bool
        # """
        self.override_str = ""
        self.AMSLogger.info("Updating jibbix options for {} with -- {}".format(self.schedule_name, options))
        self.ams_jibbix_options = AMSJibbixOptions()
        self.ams_jibbix_options.load(self.schedule_name, options)
        for key in self.allowed_jibbix_overrides:
            self.AMSLogger.debug('[JIBBIX_OPTIONS] Checking override for key: %s' % key)
            tmp_value = getattr(self.base_jibbix, key)
            if tmp_value and tmp_value != "" and getattr(self.ams_jibbix_options, key) != tmp_value:
                self.AMSLogger.debug('[OVERRIDE FOUND] Checking override for key: %s' % key)
                if self.override_str == "":
                    self.override_str += "\n"
                self.override_str += "\n[OVERRIDE %s] %s -> %s" % (key, getattr(self.ams_jibbix_options, key), tmp_value)
                setattr(self.ams_jibbix_options, key, tmp_value)

        return True

    def send_alerts_to_zabbix(self):
        """
        This method will call an Event handler
        :param :
        :return:
        """
        # AMSZabbix Event handler
        self.ams_jibbix_options.description += self.override_str
        return self.event_handler.create(self.ams_jibbix_options, description=self.ams_jibbix_options.description)

    def _move_to_processed(self):
        """
        This method will move file back file to successfully processed if sending alerts to Zabbix is success
        :return:
        """

        try:
            if not self.fev.directory_exists(self.processed_path):
                self.AMSLogger.info('%s directory does not exist, trying to create it...' % self.processed_path)
                os.makedirs(self.processed_path)

            if self.fev.directory_writeable(self.processed_path):
                processed_file = os.path.join(self.processed_path, os.path.basename(self.dest_filename_path))
                self.AMSLogger.info("File to be moved {} to processed: {}".format(self.dest_filename_path, processed_file))
                return shutil.move(self.dest_filename_path, processed_file)
            else:
                new_filename = self.dest_filename_path + '.' + strftime('%Y%m%d_%H%M%S')
                self.AMSLogger.critical('%s directory does not exist, renaming file to %s to avoid potential conflicts' % (self.processed_path, new_filename))
                return shutil.move(self.dest_filename_path, new_filename)
        except Exception as e:
            self.AMSLogger.error('Could not archive file appropriately: %s - %s ' % (self.dest_filename_path, str(e)))