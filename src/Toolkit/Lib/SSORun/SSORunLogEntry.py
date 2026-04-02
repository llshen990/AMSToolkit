import os
import sys
import logging
from datetime import datetime

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

class SSORunLogEntry(object):

    def __init__(self):
        self.AMSLogger = logging.getLogger('AMS')
        self.program = None  # type: str
        self.file = None  # type: str
        self.twait = None  # type: int
        self.elapsed = None  # type: str
        self.err_ignore_rc_string = None  # type: str
        self.end_time_str = None  # type: str
        self.end_time_obj = None  # type: datetime
        self.fullpath = None  # type: str
        self.warnings = None  # type: int
        self.logdate_str = None  # type: str
        self.logdate_obj = None  # type: datetime
        self.sasdef = None  # type: int
        self.start_time_str = None  # type:str
        self.start_time_obj = None  # type: datetime
        self.name = None  # type: str
        self.type = None  # type: str
        self.shparam = None  # type: str
        self.errors = None  # type: int
        self.status = None  # type: str
        self.dcount = None  # type: int
        self.st_seconds = None  # type: int
        self.notify = None  # type: int
        self.depend = None  # type: str
        self.altlog = None  # type: str
        self.return_code = None  # type: int
        self.et_seconds = None  # type: int
        self.elapsed_time = None  # type: str
        self.altprint = None  # type: str
        self.sso_path = None  # type: str
        self.site = None  # type: str
        self.loglink = None  # type: str
        self.customer = None  # type: str
        self.force_ckpt_rc_string = None  # type: str
        self.config = None  # type: str
        self.is_error = False

    def load(self, entry_element):
        self.program = entry_element.attrib.get('program')
        self.AMSLogger.debug('program: %s' % self.program)

        self.file = entry_element.attrib.get('file')
        self.AMSLogger.debug('file: %s' % self.file)

        self.twait = entry_element.attrib.get('twait')
        self.AMSLogger.debug('twait: %s' % self.twait)

        self.elapsed = entry_element.attrib.get('elapsed')
        self.AMSLogger.debug('elapsed: %s' % self.elapsed)

        self.err_ignore_rc_string = entry_element.attrib.get('err_ignore_rc_string')
        self.AMSLogger.debug('err_ignore_rc_string: %s' % self.err_ignore_rc_string)

        self.end_time_str = entry_element.attrib.get('end_time')
        self.AMSLogger.debug('end_time_str: %s' % self.end_time_str)

        self.fullpath = entry_element.attrib.get('fullpath')
        self.AMSLogger.debug('fullpath: %s' % self.fullpath)

        self.warnings = entry_element.attrib.get('warnings')
        self.AMSLogger.debug('warnings: %s' % self.warnings)

        self.logdate_str = entry_element.attrib.get('logdate')
        self.AMSLogger.debug('logdate_str: %s' % self.logdate_str)

        self.sasdef = entry_element.attrib.get('sasdef')
        self.AMSLogger.debug('sasdef: %s' % self.sasdef)

        self.start_time_str = entry_element.attrib.get('start_time')
        self.AMSLogger.debug('start_time_str: %s' % self.start_time_str)

        self.name = entry_element.attrib.get('name')
        self.AMSLogger.debug('name: %s' % self.name)

        self.type = entry_element.attrib.get('type')
        self.AMSLogger.debug('type: %s' % self.type)

        self.shparam = entry_element.attrib.get('shparam')
        self.AMSLogger.debug('shparam: %s' % self.shparam)

        self.errors = entry_element.attrib.get('errors')
        self.AMSLogger.debug('errors: %s' % self.errors)

        self.status = entry_element.attrib.get('status')
        self.AMSLogger.debug('status: %s' % self.status)
        if self.status in ['ERROR']:
            self.is_error = True

        self.dcount = entry_element.attrib.get('dcount')
        self.AMSLogger.debug('dcount: %s' % self.dcount)

        self.st_seconds = entry_element.attrib.get('st_seconds')
        self.AMSLogger.debug('st_seconds: %s' % self.st_seconds)

        self.notify = entry_element.attrib.get('notify')
        self.AMSLogger.debug('notify: %s' % self.notify)

        self.depend = entry_element.attrib.get('depend')
        self.AMSLogger.debug('depend: %s' % self.depend)

        self.altlog = entry_element.attrib.get('altlog')
        self.AMSLogger.debug('altlog: %s' % self.altlog)

        self.return_code = entry_element.attrib.get('return_code')
        self.AMSLogger.debug('return_code: %s' % self.return_code)

        self.et_seconds = entry_element.attrib.get('et_seconds')
        self.AMSLogger.debug('et_seconds: %s' % self.et_seconds)

        self.elapsed_time = entry_element.attrib.get('elapsed_time')
        self.AMSLogger.debug('elapsed_time: %s' % self.elapsed_time)

        self.altprint = entry_element.attrib.get('altprint')
        self.AMSLogger.debug('altprint: %s' % self.altprint)

        self.sso_path = entry_element.attrib.get('sso_path')
        self.AMSLogger.debug('sso_path: %s' % self.sso_path)

        self.site = entry_element.attrib.get('site')
        self.AMSLogger.debug('site: %s' % self.site)

        self.loglink = entry_element.attrib.get('loglink')
        self.AMSLogger.debug('loglink: %s' % self.loglink)

        self.customer = entry_element.attrib.get('customer')
        self.AMSLogger.debug('customer: %s' % self.customer)

        self.force_ckpt_rc_string = entry_element.attrib.get('force_ckpt_rc_string')
        self.AMSLogger.debug('force_ckpt_rc_string: %s' % self.force_ckpt_rc_string)

        self.config = entry_element.attrib.get('config')
        self.AMSLogger.debug('config: %s' % self.config)

    def is_job_error(self):
        return self.is_error

    def __str__(self):
        pass