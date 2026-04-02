from testfixtures import LogCapture
import logging
from pprint import pformat


class SubLogger(object):
    def __init__(self, capture, level=None):
        self.capture = capture
        self.level = level

    def assert_called(self):
        return len(self.capture.actual()) > 0

    def assert_called_with(self, level, message):
        return self.assert_any_call(level, message)

    def assert_any_call(self, level, message=None):
        if message is None:
            message = level
            level = self.level
        find = ('AMS', logging.getLevelName(level), message)
        for item in self.capture.actual():
            if hasattr(find[2], 'text') and find[2].text:
                find = (find[0], find[1], find[2].text)
            if find[0] == item[0] and find[1] == item[1] and str(item[2]).find(find[2]) >= 0:
                return True
        raise AssertionError('\n\nMessage not found in captured log messages!\nLooked for entry:\n%s\n\nActual capture:\n%s\n\n' % (pformat(find), pformat(str(self.capture))))


class MockLogger(LogCapture):
    def __init__(self):
        super(LogCapture, self).__init__()
        self.capture = LogCapture(names='AMS')
        self.log = SubLogger(self.capture)

        self.info = SubLogger(self.capture, level=logging.INFO)
        self.critical = SubLogger(self.capture, level=logging.CRITICAL)
        self.debug = SubLogger(self.capture, level=logging.DEBUG)
        self.warning = SubLogger(self.capture, level=logging.WARNING)
        self.error = SubLogger(self.capture, level=logging.ERROR)

        self.log.info = self.info
        self.log.critical = self.critical
        self.log.debug = self.critical
        self.log.warning = self.warning
        self.log.error = self.error

    def check_present(self, *expected, **kw):
        self.capture.check_present(expected, kw)

    def assert_called(self):
        return len(self.capture.actual()) > 0