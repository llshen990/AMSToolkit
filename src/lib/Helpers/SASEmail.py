import os, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Exceptions import *

import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# from email.mime.
from lib.Helpers import StripHtmlTags, Text2Html
from lib.Validators import EmailValidator

class SASEmail(object):
    """ This class will house SAS Email functionality.
    Attributes:
        email_to: This will be the list of emails separated by commas to send an email to.
        email_from: This will be the email the message is sent from.
        email_reply_to: This will be the reply-to email if different from the email_from var.
        txt_part: This is the text version of the email to support multi-part emails.
        html_part: This is the HTML version of an email to support multi-part emails.
        smtp: smtplib.SMTP instance
        subject: This is the subject of the email
        email_validator: holds an instance of EmailValidator with debug on.
    """

    def __init__(self):
        """
        This method will construct the FileShredder class, attempt to shred the file, and return boolean result.
        """
        self.email_to = ''
        self.email_from = ''
        self.email_reply_to = ''
        self.txt_part = ''
        self.html_part = ''
        self.smtp = smtplib.SMTP()
        self.msg = ''
        self.subject = ''
        self.email_validator = EmailValidator(True)
        self.set_from('replies-disabled@sas.com')

    def set_from(self, from_email):
        """
        This method will validate and set the from email address(es).
        Args:
            from_email: str

        Returns: self
        """
        from_email = str(from_email).strip()
        if not self.email_validator.validate(from_email):
            raise EmailException('Invalid from email: ' + self.email_validator.format_errors())

        self.email_from = from_email
        return self

    def set_to(self, email_to):
        """
        This method will validate and set the to email address(es).
        Args:
            email_to: str

        Returns: self
        """
        email_to = str(email_to).strip()
        if not self.email_validator.validate_email_list(email_to):
            raise EmailException('Invalid to email(s): ' + self.email_validator.format_errors())

        self.email_to = email_to
        return self

    def _email_to_fix_up(self):
        if self.email_to.find(','):
            return [x.strip() for x in self.email_to.split(',')]

        return [self.email_to]

    def set_subject(self, subject):
        """
        This method will validate and set the subject
        Args:
            subject: str

        Returns: self
        """
        subject = str(subject).strip()
        if not subject:
            raise EmailException('SASEmail requires a subject.')
        elif len(subject) > 78:
            raise EmailException('SASEmail requires subject be <= 78 characters to follow RFC-2822 standards')

        self.subject = subject
        return self

    def set_text_message(self, text_message):
        """
        This method will set and validate the text portion of the email message.
        Args:
            text_message: str

        Returns: self
        """
        text_message = str(text_message)
        if not text_message:
            raise EmailException('SASEmail requires a text message when calling set_text_message')

        self.txt_part = StripHtmlTags().strip(Text2Html(text_message).br2nl())
        return self

    def set_html_message(self, html_message):
        """
        This method will set and validate the html portion of the email message.
        Args:
            html_message: str

        Returns: self
        """
        html_message = str(html_message).strip()
        if not html_message:
            raise EmailException('SASEmail requires a html message when calling set_html_message')

        self.html_part = html_message
        return self

    def set_reply_to(self, reply_to_email):
        """
        This method will set and validate the reply-to email.
        Args:
            reply_to_email: str

        Returns: self
        """
        reply_to_email = str(reply_to_email).strip()
        if not self.email_validator.validate(reply_to_email):
            raise EmailException('Invalid reply-to email: ' + self.email_validator.format_errors())

        self.email_reply_to = reply_to_email
        return self

    def _create_message(self):
        """
        This method will create and send the email message.  It will also do some validations and setup appropriate headers.
        Returns: bool

        """
        try:
            if not self.txt_part and not self.html_part:
                raise EmailException('You must have at least one text or html message')
            elif self.txt_part and self.html_part:
                self.msg = MIMEMultipart('alternative')
                part_txt = MIMEText(self.txt_part, 'plain')
                part_html = MIMEText(self.html_part, 'html')
                self.msg.attach(part_txt)
                self.msg.attach(part_html)
            elif self.html_part:
                self.set_text_message(StripHtmlTags().strip(Text2Html(self.html_part).br2nl()))
                self.msg = MIMEMultipart('alternative')
                part_txt = MIMEText(self.txt_part, 'plain')
                part_html = MIMEText(self.html_part, 'html')
                self.msg.attach(part_txt)
                self.msg.attach(part_html)
            else:
                self.msg = MIMEText(self.txt_part)

            self.msg['Subject'] = self.subject
            self.msg['From'] = self.email_from
            self.msg['To'] = self.email_to
            if not self.email_reply_to:
                self.set_reply_to(self.email_from)

            self.msg.add_header('reply-to', self.email_reply_to)
            self.smtp.sendmail(self.email_from, self._email_to_fix_up(), self.msg.as_string())
            self.smtp.quit()

            return True
        except Exception as e:
            raise EmailException('[ERROR] Problem sending email: ' + str(e))

    def send(self):
        """
        This method is invoke the message sending.
        :return: bool
        """
        return self._create_message()