# @author owhoyt
import abc
import os.path
import sys
import ConfigParser
import traceback
from collections import OrderedDict
from AbstractScenario import AbstractScenario

from lib.Helpers import OutputFormatHelper, Logger, SASEmail
from datetime import datetime
from lib.Validators import BoolValidator, EmailValidator
from lib.Exceptions import EmailException, EmailSuccessException, EmailSkipException

class AbstractEmailTemplate(AbstractScenario):
    __metaclass__ = abc.ABCMeta

    def __init__(self, debug=False):
        AbstractScenario.__init__(self, debug=debug)

        # set some defaults / setup some config data
        self.config = ConfigParser.ConfigParser()
        self.config.read(AbstractScenario.APP_PATH + '/Config/ssod_validator.cfg')

        self.test_mode = None

        self.data = OrderedDict()

        self.header = ''
        self.body = ''
        self.footer = ''
        self.view_vars = OrderedDict()
        self.html = ''
        self.views_dir = AbstractScenario.APP_PATH + '/EmailTemplates/Templates/views/'

        self.email_list = None
        self.subject = None

        self.txt_only_version = ''
        self.market = None

    @abc.abstractmethod
    def get_data(self):
        return

    @abc.abstractmethod
    def set_body(self):
        return

    @abc.abstractmethod
    def set_subject(self, data):
        return

    @abc.abstractmethod
    def post_email_send_handler(self):
        return

    def init_email(self, email_list, market_name, test_mode, subject):
        self.log_it('Initing email')
        bool_val = BoolValidator(True)
        if not bool_val.validate(test_mode):
            raise EmailException('Invalid test mode parameter.  Must be a boolean value: ' + bool_val.format_errors())

        self.test_mode = test_mode

        self.subject = subject

        market = market_name.strip()

        if not market:
            raise EmailException('Market name is required.')

        self.market = market.upper()

        email_validator = EmailValidator(True)
        self.email_list = email_validator.validate_email_list(email_list)
        if not self.email_list:
            raise EmailException('Invalid email addresses: ' + os.linesep + email_validator.format_errors())
        try:
            self.log_it('Getting data...')
            self.get_data()
            self.log_it('Setting subject...')
            self.set_subject(self.market)
            self.log_it('Rendering email...')
            self.render_email()
        except EmailSuccessException:
            self.log_it('Calling post email send helper...')
            self.post_email_send_handler()
            raise
        except EmailSkipException:
            raise
        except Exception as e:
            traceback.print_exc()
            raise EmailException('Caught error trying to send email: ' + str(e))

    def render_email(self):
        self.log_it('Calling set_header...')
        self.set_header()
        self.log_it('Calling set_footer...')
        self.set_footer()
        self.log_it('Calling set_body...')
        self.set_body()
        self.log_it('Combining header, body and footer...')
        self.combine_email()
        if self.test_mode:
            self.test_email()
        else:
            self.send_email()

    def set_header(self):
        self.log_it('In set_header for ' + str(self))
        with open(self.views_dir + '/headers/' + str(self) + '.html', 'r') as header_file:
            self.header = header_file.read()

    def set_footer(self):
        self.log_it('In set_footer for ' + str(self))
        with open(self.views_dir + '/footers/' + str(self) + '.html', 'r') as footer_file:
            self.footer = footer_file.read()

    def combine_email(self):
        self.log_it('In combine_email for ' + str(self))
        self.html = self.header + self.body + self.footer

        if self.is_debug_enabled():
            with open(AbstractScenario.APP_PATH + '/' + str(self) + '.html', "w") as output_file:
                output_file.write(self.html)

    def get_view(self, view, replace_vars=None):
        try:
            with open(self.views_dir + '/' + str(self) + '/' + view + '.html', 'r') as view_file:
                if replace_vars is None or not isinstance(replace_vars, dict):
                    return view_file.read()
                else:
                    template_data = view_file.read()
                    for key, value in replace_vars.iteritems():
                        template_data = template_data.replace('{' + key + '}', value)
                    return template_data
        except Exception as e:
            raise EmailException('Could not get view ' + view + ': ' + str(e))

    def send_email(self):

        sas_email = SASEmail()
        sas_email.set_from('replies-disabled@sas.com')
        sas_email.set_to(self.email_list)
        sas_email.set_subject(self.subject)
        sas_email.set_html_message(self.html)
        sas_email.set_text_message(self.txt_only_version)
        sas_email.send()
        raise EmailSuccessException('Email has been sent successfully.')

    def test_email(self):
        print self.html
        raise EmailSuccessException('Email has been sent printed.')

    def log_name(self):
        return 'email_template'

