# @author owhoyt
import abc
import os, sys
# noinspection PyUnresolvedReferences
import readline
import logging

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)


class AbstractView(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.debug = False
        self.data = None
        self.input_data = None
        self.AMSLogger = logging.getLogger('AMS')

    @abc.abstractmethod
    def render(self):
        return

    @abc.abstractmethod
    def get_data(self):
        return

    @abc.abstractmethod
    def init(self):
        return

    def set_input_data(self, input_data):
        self.input_data = input_data

    # noinspection PyMethodMayBeStatic
    def __whoami(self):
        # noinspection PyProtectedMember
        return sys._getframe(1).f_code.co_name