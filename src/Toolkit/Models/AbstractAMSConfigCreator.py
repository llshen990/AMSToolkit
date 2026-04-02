import os
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Models.AbstractAMSBase import AbstractAMSBase

class AbstractAMSConfigCreator(AbstractAMSBase):

    def __init__(self, ams_config):
        AbstractAMSBase.__init__(self, ams_config)

    def write_config(self):
        self.AMSConfig.write_config()