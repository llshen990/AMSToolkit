import os
import time


class AMSFile(object):
    def __init__(self):
        pass

    @staticmethod
    def remove(path):
        with open(path, 'rw'):
            os.remove(path)

    @staticmethod
    def clear(path):
        with open(path, 'rw'):
            millis = str(int((time.time())))
            # TODO: check or manage the number of . files?
            os.rename(path,  os.path.dirname(path) + os.sep + '.' + os.path.basename(path) + '.' + millis)
