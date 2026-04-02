class MockFindValidator(object):
    def __init__(self, text):
        """
        :param text: string
        """
        self.text = str(text)

    def __eq__(self, other):
        """
        :param other: string
        """
        # Checks to ensure the provided text exists in the given other string
        return other.find(self.text) >= 0