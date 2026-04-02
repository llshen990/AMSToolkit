import uuid


class TestHelpers(object):
    def __init__(self):
        pass

    @staticmethod
    def get_unique_file_name():
        return str(uuid.uuid4())

