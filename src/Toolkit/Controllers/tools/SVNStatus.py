import subprocess

import logging
import os
import datetime
import re

from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Lib import AMSLogger
from Toolkit.Config import AMSConfig, AMSJibbixOptions
from Toolkit.Exceptions import AMSException


class SVNStatus(object):
    def __init__(self, ams_config, path, tla, command='svn'):
        self.ams_config = ams_config  # type: AMSConfig
        self.logger = logging.getLogger('AMS')
        self.logger.setLevel(logging.DEBUG)
        self.path = os.path.abspath(path)
        self.logger.info("Using dirname of path={} as actual path (path provided was {})".format(self.path, path))

        self.tla = tla
        if command not in ('svn', 'git'):
            raise Exception('Source control type={} is not supported'.format(command))
        self.command = command

        # Common jibbix
        self.jibbix = AMSJibbixOptions()
        self.jibbix.project = self.tla
        self.jibbix.security = "sas"
        self.jibbix.type = "issue"
        self.jibbix.priority = "critical"
        self.jibbix.labels = "Lev1"
        self.jibbix.merge = "simple"
        self.jibbix.assignee = "ssoretailops"

        self.doclink = 'Consult the SharePoint documentation and adjust the configuration as needed\n\n[Source Code Manager Sharepoint Documentation|https://sasoffice365.sharepoint.com/sites/MASETLOperations/SitePages/Source-Code-Manager.aspx]'

    def evaluate_response(self, response, separator):
        svn_status = ['A', 'D', 'M', 'R', 'C', 'X', '?', '!', '~']
        not_working_copy = 'is not a working copy'

        svn_responses = response.strip().split(separator)
        self.logger.debug('check returned responses={}'.format(svn_responses))

        if len(svn_responses) > 0:
            first_line = svn_responses[0]
            if first_line == '':
                self.logger.info("No changes")
            else:
                self.logger.info('Response is responses={}'.format(svn_responses))

                if not_working_copy in first_line:
                    self.logger.info("No a valid repository")
                    # This creates a ticket
                    self.zabbix_not_in_svn()
                else:
                    if first_line and first_line.split()[0] in svn_status:
                        self.logger.info("There are uncommitted files")
                        # This creates a ticket
                        self.zabbix_files_not_committed(svn_responses)
                    else:
                        self.logger.info("Some modification exists with the repository response={}".format(response))
                        # This creates a ticket
                        self.zabbix_repository_changes_not_clean(svn_responses)

    def get_status(self, arg='--porcelain=v1'):
        """
        Currently executes the source code control status command through the OS
        results to
        :return:
        """

        svn_status = ['A', 'D', 'M', 'R', 'C', 'X', '?', '!', '~']
        not_working_copy = 'is not a working copy'
        args = [self.command, 'status']

        try:
            separator = '\n'
            if self.command == 'svn':
                args.append(self.path)
            elif self.command == 'git':
                args.append(arg)
                separator = '\0'

            self.logger.info("Running command='{}' to determine status for {}".format(" ".join(args), self.command))
            self.evaluate_response(subprocess.check_output(args, cwd=self.path, stderr=subprocess.STDOUT), separator)

        except Exception as e:
            self.logger.info("Some exception happened examining responses")
            if re.search('exit status 129', str(e)) is not None and arg != '--porcelain':
                self.logger.info("Exit status 129 was detected.")
                self.get_status(arg='--porcelain')
            else:
                self.zabbix_error_with_svn(args, e)
                raise AMSException("Call to {} returned error '{}'".format(self.command, e))

    def zabbix_files_not_committed(self, responses):
        self.jibbix.summary = "Source Code Manager: Files not committed to {}".format(self.command)
        self.jibbix.comment = "{}\n{} files not committed in path={}\n\nRun '{} status' from the path to see " \
                              "files not committed.\n\n".format(datetime.date.today(), len(responses), self.path, self.command)
        self.jibbix.comment += "Please add, commit, or ignore these files as needed:\n {}\n\n".format('\n'.join(responses))
        self.jibbix.comment += '{}'.format(self.doclink)
        self.create_ticket()

    def zabbix_repository_changes_not_clean(self, responses):
        self.jibbix.summary = "Source Code Manager: Status is not clean {}".format(self.command)
        self.jibbix.comment = "{}\n{} files need to be investigated in path={}\n\nRun '{} status' from the path to see " \
                              "the related files.\n\n".format(datetime.date.today(), len(responses), self.path, self.command)
        self.jibbix.comment += "Please add, commit, or ignore these files as needed:\n {}\n\n".format('\n'.join(responses))
        self.jibbix.comment += '{}'.format(self.doclink)
        self.create_ticket()

    def zabbix_not_in_svn(self):
        self.jibbix.summary = "Source Code Manager: Configured Directory Not Under {}".format(self.command)
        self.jibbix.comment = "{}\nThe {} repository at path={} is not a valid repository\n\n".format(datetime.date.today(), self.command, self.path)
        self.jibbix.comment += "{}".format(self.doclink)
        self.create_ticket()

    def zabbix_error_with_svn(self, args, x):
        self.jibbix.summary = "Source Code Manager: Error with {} check".format(self.command, self.command)
        if isinstance(x, subprocess.CalledProcessError):
            e = x  # type: subprocess.CalledProcessError
            self.jibbix.comment = "{}\nThe command '{}' had an error\n\n" \
                                  "returncode={}\n" \
                                  "path={}\n\n" \
                                  "{}\n\n{}".format(datetime.date.today(), str.join(' ', args), e.returncode, self.path, e.output, self.doclink)
        elif isinstance(x, OSError):
            e = x  # type: OSError
            self.jibbix.comment = "{}\nThe command '{}' had an OSError\n\n" \
                                  "errno={}\n" \
                                  "strerror={}\n\n" \
                                  "{}\n\n{}".format(datetime.date.today(), str.join(' ', args), e.errno, self.path, e.strerror, self.doclink)
        else:
            e = x  # type: Exception
            self.jibbix.comment = "{}\nThe command '{}' had an Exception\n\n" \
                                  "path={}\n\n" \
                                  "{}\n\n{}".format(datetime.date.today(), str.join(' ', args), self.path, str(e), self.doclink)
        self.create_ticket()

    def create_ticket(self):
        zabbix = AMSZabbix(self.logger, config=self.ams_config)
        zabbix.call_zabbix_sender(AMSDefaults().default_zabbix_key_no_schedule, self.jibbix.str_from_options())


if __name__ == '__main__':
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log', log_path_override='/tmp')
    x = SVNStatus(AMSConfig(), '', 'XYZ', command='git')
    # x.evaluate_response('1 .M N... 100644 100644 100644 b2b689ac88ecb0e7a85fe10ededd040dab95d83d b2b689ac88ecb0e7a85fe10ededd040dab95d83d bypass_dates.txt', '\n')
    # x.evaluate_response('', '\n')
    x.evaluate_response(' M conf/bypass_dates.txt', '\n')
    #x.evaluate_response('?? current', '\n')