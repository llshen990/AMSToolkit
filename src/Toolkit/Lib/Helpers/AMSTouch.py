import os

class AMSTouch(object):
    def __init__(self):
        pass

    @staticmethod
    def touch(path):
        with open(path, 'a'):
            os.utime(path, None)