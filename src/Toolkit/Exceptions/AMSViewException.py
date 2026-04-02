# @author owhoyt
import logging


class AMSViewException(Exception):
    def __init__(self, message):
        logging.getLogger('AMS').critical(str(message))

        super(AMSViewException, self).__init__(message)