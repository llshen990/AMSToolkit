import os
import sys
import logging
from datetime import datetime
import lxml.etree as etree
from lxml.etree import XMLSyntaxError
from collections import OrderedDict
import time

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.SSORun import SSORunLogEntry
from lib.Validators import FileExistsValidator
from Toolkit.Exceptions import AMSSSORunLogException


class SSORunLog(object):

    def __init__(self):
        self.AMSLogger = logging.getLogger('AMS')
        self.entries = OrderedDict()  # type: OrderedDict[str, SSORunLogEntry]
        self.customer = None  # type: str
        self.site = None  # type: str
        self.datetime_str = None  # type: str
        self.datetime_obj = None  # type: datetime
        self.logdate_str = None  # type: str
        self.logdate_obj = None  # type: datetime
        self.logdate_from = None  # type: str
        self.working_directory = None  # type: str
        self.config = None  # type:str
        self.schedule = None  # type: str
        self.sso_path = None  # type: str
        self.fev = FileExistsValidator(True)

        self.jobs_in_error = OrderedDict()  # type: OrderedDict[str, SSORunLogEntry]
        self.error = False

    def parse_sso_run_log(self, path_to_file):
        if not self.fev.validate(path_to_file):
            raise AMSSSORunLogException('SSO Run Log file does not exist: %s' % path_to_file)

        # need to reset the lists
        self.jobs_in_error = OrderedDict()
        self.entries = OrderedDict()
        parse_successful = False
        parse_attempts = 0
        parse_max_attempts = 3
        parse_sleep_duration = 5

        while not parse_successful:
            try:
                parser = etree.XMLParser(recover=True)
                tree = etree.parse(path_to_file, parser=parser)
                parse_successful = True
            except XMLSyntaxError:
                if parse_attempts < parse_max_attempts:
                    parse_attempts += 1
                    time.sleep(parse_sleep_duration)
                else:
                    raise

        # tree = ElementTree.parse(path_to_file)
        self.load(tree.getroot())
        self.load_entries(tree)

    def load(self, sso_log_element):
        self.customer = sso_log_element.attrib.get('customer')
        self.AMSLogger.debug('customer: %s' % self.customer)

        self.site = sso_log_element.attrib.get('site')
        self.AMSLogger.debug('site: %s' % self.site)

        self.datetime_str = sso_log_element.attrib.get('datetime')
        self.AMSLogger.debug('datetime_str: %s' % self.datetime_str)

        self.logdate_str = sso_log_element.attrib.get('logdate')
        self.AMSLogger.debug('logdate_str: %s' % self.logdate_str)

        self.logdate_from = sso_log_element.attrib.get('logdate_from')
        self.AMSLogger.debug('logdate_from: %s' % self.logdate_from)

        self.working_directory = sso_log_element.attrib.get('working_directory')
        self.AMSLogger.debug('working_directory: %s' % self.working_directory)

        self.config = sso_log_element.attrib.get('config')
        self.AMSLogger.debug('config: %s' % self.config)

        self.schedule = sso_log_element.attrib.get('schedule')
        self.AMSLogger.debug('schedule: %s' % self.schedule)

        self.sso_path = sso_log_element.attrib.get('sso_path')
        self.AMSLogger.debug('sso_path: %s' % self.sso_path)

    def load_entries(self, tree):
        element_cnt = 0
        for element in tree.findall('entry'):
            element_cnt += 1
            self.AMSLogger.debug('----------------- Start SSORun Entry entry #%s -----------------' % element_cnt)
            ams_sso_run_log_entry = SSORunLogEntry()
            ams_sso_run_log_entry.load(element)
            self.entries[ams_sso_run_log_entry.name] = ams_sso_run_log_entry

            if ams_sso_run_log_entry.is_job_error():
                self.error = True
                self.jobs_in_error[ams_sso_run_log_entry.name] = ams_sso_run_log_entry

            self.AMSLogger.debug('----------------- End SSORun Entry entry #%s -------------------' % element_cnt)

    def __str__(self):
        pass