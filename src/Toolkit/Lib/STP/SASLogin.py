"""
requests: http://docs.python-requests.org/en/master/ (can be installed by running command: pip install requests)
"""

import re
import requests
import os
import sys
import logging
import urllib

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from requests.exceptions import Timeout, ConnectionError
from Toolkit.Lib import AMSWebReturnCode

class SASLogin(object):
    """
    This class handles the login business logic for successfully logging into SAS's web applications
    """

    def __init__(self):
        self.session = requests.Session()
        self.url = None  # type: str
        self.username = None  # type: str
        self.password = None  # type: str
        self.proxies = None  # type: str
        self.headers = None  # type: str
        self.timeout = 30  # type: int
        self.ssl = True
        self.AMSWebReturnCode = None  # type: AMSWebReturnCode
        self.ams_logger = logging.getLogger('AMS')

    def login(self, url, username, password):
        """
        This method will return AMSWebReturnCode object for a url request with username and password credentials
        :param url: URL to login to.
        :type url: str
        :param username: Username to login with
        :type username: str
        :param password: Password to login with
        :type password: str
        :return: AMSWebReturnCode
        :rtype: AMSWebReturnCode
        """
        payload = {}
        self.AMSWebReturnCode = AMSWebReturnCode(url)
        self.AMSWebReturnCode.url = url

        try:
            req = self.session.get(url, timeout=self.timeout, headers=self.headers, proxies=self.proxies,
                                   verify=self.ssl)
            self.ams_logger.debug("Get request at %s, returns status code %s" % (str(url), str(req.status_code)))
            self.AMSWebReturnCode.data = req.text
            self.AMSWebReturnCode.status_code = req.status_code

            login_form = re.findall(r'<form id="(.*?)"', req.text, re.S | re.M | re.UNICODE)
            login_div = re.findall(r'<div id="(.*?)"', req.text, re.S | re.M | re.UNICODE)
            self.ams_logger.debug('login_form: %s' % login_form)

            flag = False

            if login_form or login_div:
                flag = True

            # SAS Logon Manager v9.3 id = "LogonForm" (at least for MISTK)
            # SAS Logon Manager v9.4 id = "fm1" (at least for ESR and FHC)
            # SAS Logon Manager Viya is div with id = "loginForm" (at least for SASStudio)

            if flag and login_form and (login_form[0] in ["fm1", "LogonForm"] or login_div[0] in ["fm1", "LogonForm", "loginForm"]):
                login_inputs = re.findall(r'<input (.*?)>', req.text, re.S | re.M | re.UNICODE)
                form_action = re.findall(r'action="(.*?)"', req.text, re.S | re.M | re.UNICODE)
                data_dojo_type = re.findall(r'data-dojo-type="(.*?)"', req.text, re.S | re.M | re.UNICODE)

                post_url = url

                if form_action:
                    self.ams_logger.debug('form_action: %s' % form_action[0])
                    self.ams_logger.debug('form_action -> found')
                    self.ams_logger.debug('post_url before: %s' % post_url)
                    if form_action[0] == 'Logon.do':
                        self.ams_logger.debug('req.url: %s' % req.url)
                        post_url = "/".join(req.url.split("/")[:-1]) + '/' + form_action[0]
                    else:
                        post_url = "/".join(req.url.split("/")[:3]) + form_action[0]
                    self.ams_logger.debug('post_url after: %s' % post_url)
                elif data_dojo_type and data_dojo_type[0] in ['dijit.form.Form']:
                    post_url = req.url + "sasexec/sessions"  # used by Viya

                self.AMSWebReturnCode.url = post_url

                if not login_inputs:
                    self.AMSWebReturnCode.add_error("Error: Empty Payload")
                    return self.AMSWebReturnCode

                for login_item in login_inputs:
                    name = re.findall(r'name="(.*?)"', login_item, re.S | re.M | re.UNICODE)
                    value = re.findall(r'value="(.*?)"', login_item, re.S | re.M | re.UNICODE)
                    input_type = re.findall(r'type="(.*?)"', login_item, re.S | re.M | re.UNICODE)

                    if input_type and input_type[0] in ['submit', 'checkbox']:
                        continue

                    if name and value:
                        payload[name[0]] = value[0]
                    else:
                        self.AMSWebReturnCode.add_error("Error: Empty Payload")
                        return self.AMSWebReturnCode

                if "username" in payload:  # used by v9.4
                    payload["username"] = username
                elif "ux" in payload:  # used by v9.3
                    payload["ux"] = username
                elif "user" in payload:  # used by Viya
                    payload["user"] = username
                if "password" in payload:  # used by v9.4 and Viya
                    payload["password"] = password
                elif "px" in payload:  # used by v9.3
                    payload["px"] = password

                self.ams_logger.debug("Post request payload keys: %s" % str(payload.keys()))
                self.ams_logger.debug("Posting to: %s" % str(post_url))

                req = self.session.post(post_url, data=payload, timeout=self.timeout, headers=self.headers,
                                        proxies=self.proxies, verify=self.ssl)
                self.AMSWebReturnCode.data = req.text
                self.AMSWebReturnCode.status_code = req.status_code

                if req.status_code == 200:
                    self.check_login(req.text, req.headers)
                    self.ams_logger.debug('Errors: %s' % self.AMSWebReturnCode.format_errors())
                else:
                    self.AMSWebReturnCode.add_error(
                        "Error: Expecting Status Code of 200, returned Status Code of %s" % str(req.status_code))
            else:
                self.AMSWebReturnCode.add_error("Error: Could not find Login Form.")
        except Timeout as E:
            self.AMSWebReturnCode.add_error("Error: Page Timeout: %s" % str(E))
        except ConnectionError as E:
            self.AMSWebReturnCode.add_error("Error: Connection Error: %s" % str(E))
        except Exception as E:
            self.AMSWebReturnCode.add_error("Error: Unknown Exception: %s" % str(E))

        return self.AMSWebReturnCode

    def logout(self, url):
        """
        This method will return AMSWebReturnCode object for a url to logout from.  Typically same URL as login.
        :param url: URL to login to.
        :type url: str
        :return: AMSWebReturnCode
        :rtype: AMSWebReturnCode
        """
        self.AMSWebReturnCode = AMSWebReturnCode(url)
        self.AMSWebReturnCode.url = url

        try:
            req = self.session.get(url, timeout=self.timeout)
            self.ams_logger.debug("Get request at %s, returns status code %s" % (str(url), str(req.status_code)))

            self.AMSWebReturnCode.data = req.text
            self.AMSWebReturnCode.status_code = req.status_code

            form_action = re.findall(r'action="(.*?)"', req.text, re.S | re.M | re.UNICODE)
            error_message = re.findall(r'\"workspaceConnectionErrorMessage\":(.*?)\"sasOS\"', req.text, re.S | re.M | re.UNICODE)

            logout_url = "/".join(req.url.split("/")[:-1]) + "/Logoff"  # used by v9.4

            if error_message:
                workspace_id = re.findall(r'\"id\":\"(.*?)"', req.text, re.S | re.M | re.UNICODE)
                # test id with working environment for Workspace Connection Error
                logout_url = req.url + "/" + workspace_id[0]
                self.AMSWebReturnCode.url = logout_url

                req = self.session.delete(logout_url)
                self.ams_logger.debug("Delete Session with url %s, returns status code %s" % (str(logout_url), str(req.status_code)))

            elif form_action:
                if "/SASLogon/Logon" in form_action[0]:
                    logout_url = "/".join(logout_url.split("/")[:3]) + "/SASLogon/Logoff.do"  # used by v9.3
                elif "/SASLogon/login" in form_action[0]:
                    logout_url = "/".join(logout_url.split("/")[:3]) + "/SASLogon/logout"  # used by unvtest

                self.AMSWebReturnCode.url = logout_url

                req = self.session.get(logout_url, timeout=self.timeout)
                self.ams_logger.debug("Logout: Get request at %s, returns status code %s" % (str(logout_url), str(req.status_code)))

            self.AMSWebReturnCode.data = req.text
            self.AMSWebReturnCode.status_code = req.status_code

            if req.status_code == 200:
                self.AMSWebReturnCode.set_result(True)
            else:
                self.AMSWebReturnCode.add_error(
                    "Error: Expecting Status Code of 200, returned Status Code of %s" % str(req.status_code))
        except Timeout as E:
            self.AMSWebReturnCode.add_error("Error: Page Timeout: %s" % str(E))
        except ConnectionError as E:
            self.AMSWebReturnCode.add_error("Error: Connection Error: %s" % str(E))
        except Exception as E:
            self.AMSWebReturnCode.add_error("Error: Unknown Exception: %s" % str(E))

        return self.AMSWebReturnCode

    def check_login(self, webpage, headers):
        """
        This method will check the response text for Login Success or Failure
        :param webpage: Web page data
        :type webpage: str
        :param headers: Response headers dictionary
        :type headers: dict
        :return: None
        :rtype: None
        """
        message = re.findall(r'<h2.*>(.*?)</h2>', webpage, re.S | re.M)
        workspace_id = re.findall(r'<div id=\"(.*?)"', webpage, re.S | re.M | re.UNICODE)

        self.ams_logger.debug('message: %s' % message)
        self.ams_logger.debug('workspace_id: %s' % workspace_id[0])

        if message:
            if message[0] in ["You have signed in.", "Log In Successful"] or "You have signed in." in webpage or "Log In Successful" in webpage:
                self.AMSWebReturnCode.set_result(True)
            elif message[0].__contains__("valid"):
                self.AMSWebReturnCode.add_error("Error: Invalid Credentials")
        elif 'Log Off' in webpage:
            self.AMSWebReturnCode.set_result(True)
        elif "Browser not supported" in webpage:
            self.AMSWebReturnCode.add_error("Error: Browser not supported")
        elif re.findall(r'<h3 .*? style="font-size: 1em; font-weight: 700; .*?>(.*?)</h3>', webpage, re.S | re.M):
            error_message = re.findall(r'<h3 .*? style="font-size: 1em; font-weight: 700; .*?>(.*?)</h3>', webpage, re.S | re.M)
            self.ams_logger.debug('error_message: %s ' % error_message)
            self.AMSWebReturnCode.add_error("Error: Access Deny: %s" % str(error_message[0]))  # error message for access deny in v9.4
        elif re.findall(r'<span .*? class="solutionsSmallItem" .*?>(.*?)</span>', webpage, re.S | re.M):
            error_message = re.findall(r'<span .*? class="solutionsSmallItem" .*?>(.*?)</span>', webpage, re.S | re.M)
            self.AMSWebReturnCode.add_error("Error: %s" % str(error_message[0]))  # error message in v9.3
        elif "workspaceConnectionError" in webpage:
            error_message = re.findall(r'\"workspaceConnectionErrorMessage\":(.*?)\"sasOS\"', webpage, re.S | re.M | re.UNICODE)
            self.AMSWebReturnCode.add_error("Error: Workspace Connection Error: %s" % str(error_message[0]))  # Get the error message for SAS Studio Workspage Server failure on SAS9.4M2+/Viya
        elif headers and 'Exception' in headers and headers['Exception'] is not None:
            error_message = urllib.unquote(headers['Exception']).replace("\"", "")
            self.AMSWebReturnCode.add_error("Error: Workspace Connection Error: %s" % str(error_message))  # Get the error message for SAS Studio Workspage Server failure on SAS9.4M1
        elif workspace_id:
            if "message1" or "message" or "status" or "msg" in workspace_id:
                error_message = re.findall(r'<h2>(.*?)</h2>', webpage, re.S | re.M)
                if error_message:
                    self.AMSWebReturnCode.add_error("Error: Workspace ID Error: %s" % str(error_message[0]))