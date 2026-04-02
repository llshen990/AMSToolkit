import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))

class Dict2Obj(object):
    """
    Turns a dictionary into a class
    """

    # ----------------------------------------------------------------------
    def __init__(self, dictionary):
        """Constructor"""
        for key in dictionary:
            setattr(self, key, dictionary[key])

    # ----------------------------------------------------------------------
    def __repr__(self):
        """"""
        return "<Dict2Obj: %s>" % self.__dict__