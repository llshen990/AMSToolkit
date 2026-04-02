# @author owhoyt
class AGPStatsException(Exception):
    def __init__(self, message):
        super(AGPStatsException, self).__init__(message)