from datetime import datetime, timedelta

class Seconds2Time(object):

    def __init__(self, sec=None, start_complete=None):
        self.sec = sec
        self.start_complete = start_complete


    def calculate_time_readable(self):
        """
        This method calculates how long the automation took to complete.
        :return: Formatted string in Days, Hours, Minutes and Seconds.
        :rtype: str
        """
        start = self.start_complete.get('start')
        complete = self.start_complete.get('complete')

        if complete is None:
            time_diff = datetime.now() - start
        else:
            time_diff = complete - start

        days, seconds = time_diff.days, time_diff.seconds
        hours = days * 24 + seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = (seconds % 60)

        return self._format_time(days, hours, minutes, seconds)


    def convert2readable(self):
        """
        This method converts seconds to a human readable string.
        :return: Formatted string in Days, Hours, Minutes and Seconds.
        :rtype: str
        """
        t = timedelta(seconds=long(self.sec))
        d = datetime(1, 1, 1) + t

        return self._format_time(t.days, d.hour, d.minute, d.second)


    def _format_time(self, day, hour, minute, second):

        ret_str = ''

        include_below = False
        if day > 0:
            ret_str += '{} Days '.format(day)
            include_below = True

        if include_below or hour > 0:
            ret_str += '{} Hours '.format(hour)
            include_below = True

        if include_below or minute > 0:
            ret_str += '{} Minutes '.format(minute)
            include_below = True

        if include_below or second > 0:
            ret_str += '{} Seconds'.format(second)

        if ret_str == '':
            ret_str = '< 1 second'

        return ret_str




