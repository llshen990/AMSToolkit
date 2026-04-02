import sys
from datetime import datetime
import os
import traceback
import random
import string
import time

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from Toolkit.Config import AMSProject, AMSJibbixOptions, AMSSchedule
from Toolkit.Exceptions import AMSException
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase

class AMSProjectConfig(AbstractAMSBase):

    def __init__(self, ams_config, project):
        """
        This is the init method to instantiate an AMSRouteFiles object.
        :param ams_config: Loaded AMSConfig object.
        :type ams_config: AMSConfig
        """

        AbstractAMSBase.__init__(self, ams_config)

        self.project = project  # type: AMSProject

    def remove_schedule(self, schedule_name):
        if schedule_name in self.project.AMSSchedules:
            del self.project.AMSSchedules[schedule_name]
            self.AMSConfig.write_config()
        else:
            raise AMSException("Schedule " + schedule_name + " does not exist in config")

    def add_schedule(self, schedule_name):
        # ensure schedule exists
        if not FileExistsValidator(True).validate(schedule_name):
            raise AMSException("Schedule file " + schedule_name + " does not exist")

        if schedule_name in self.project.AMSSchedules:
            self.AMSLogger.warning("Schedule " + schedule_name + " already exists in config")
            return

        new = AMSSchedule()

        # this is a hack for now but will get the job done
        new.debug = self.AMSConfig.debug
        new.schedule_name = schedule_name
        new.home_dir = self.project.home_dir
        new.signal_dir = self.project.signal_dir
        new.schedule_config_file = self.project.home_dir + "/conf/" + "config.txt"
        new.automation_type = 'SSORun'
        new.tla = self.AMSConfig.get_my_environment().tla
        new.incoming_dir = self.AMSConfig.incoming_dir
        new.outgoing_dir = self.AMSConfig.outgoing_dir
        new.archive_dir = self.AMSConfig.archive_dir
        new.AMSJibbixOptions.project = new.tla
        new.AMSJibbixOptions.schedule_name = new.schedule_name
        new.AMSJibbixOptions.priority = 'critical'
        new.AMSJibbixOptions.security = 'none'
        new.AMSJibbixOptions.host = self.AMSConfig.my_hostname

        self.project.AMSSchedules[new.schedule_name] = new
        self.AMSConfig.write_config()

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name