class Text2Html(object):
    """
    This class contains some helpers to change between text and HTML.
    Attributes:
        input: str
    """

    def __init__(self, input_str):
        """
        Args:
            input_str: str
        """
        self.input = str(input_str)

    def nl2br(self, is_xhtml=True):
        """
        Will replace "\n" with "<br />"
        Args:
            is_xhtml: bool

        Returns: str

        """
        if is_xhtml:
            return self.input.replace('\n', '<br />\n')
        else:
            return self.input.replace('\n', '<br>\n')

    def br2nl(self):
        """
        Will replace "<br />" with "\n"
        Returns: str

        """
        self.input = self.input.replace('<br />', '\n')
        self.input = self.input.replace('<br>', '\n')
        self.input = self.input.replace('<br/>', '\n')
        self.input = self.input.replace('<BR />', '\n')
        self.input = self.input.replace('<BR>', '\n')
        self.input = self.input.replace('<BR/>', '\n')

        return str(self.input)
