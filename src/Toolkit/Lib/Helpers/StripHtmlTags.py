from HTMLParser import HTMLParser


class StripHtmlTags(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)

    def strip(self, html):
        self.feed(html)
        return self.get_data()
