from sys import version_info

# For Python 2 and 3 compatibility
if version_info[0] == 2:
    res_type = str
elif version_info[0] >= 3:
    res_type = bytes


class MockResponse(object):
    def __init__(self, ret, code=200, msg='OK'):
        self.ret = ret
        self.code = code
        self.msg = msg
        self.headers = {'content-type': 'text/plain; charset=utf-8'}

    def read(self):
        return res_type(self.ret.encode('utf-8'))

    def getcode(self):
        return self.code
