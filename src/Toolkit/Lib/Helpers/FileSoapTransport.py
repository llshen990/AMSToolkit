import os
from zeep import Client, Transport
from urlparse import urlparse
import logging

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))

class FileSoapTransport(Transport):
    def load(self, url):
        if not url:
            raise ValueError("No url given to load")
        parsed_url = urlparse(url)

        logging.getLogger('AMS').debug('Loading url=%s' % str(parsed_url))

        if parsed_url.scheme in ('http', 'https'):
            if parsed_url.netloc == "schemas.xmlsoap.org":
                logging.getLogger('AMS').info('Local file loading for url=%s' % str(parsed_url))
                url = APP_PATH + '/../../config/soap/' + parsed_url.path[1:].replace('/', '.') + "xml"
            else:
                response = self.session.get(url, timeout=self.load_timeout)
                response.raise_for_status()
                return response.content
        elif parsed_url.scheme == 'file':
            if url.startswith('file://'):
                url = url[7:]
        with open(os.path.expanduser(url), 'rb') as fh:
            return fh.read()