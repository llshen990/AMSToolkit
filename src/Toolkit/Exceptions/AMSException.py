# @author owhoyt
import logging


class AMSException(Exception):
    def __init__(self, message):
        # @todo: change to grab the singleton / instance
        logging.getLogger('AMS').exception(str(message))

        super(AMSException, self).__init__(message)