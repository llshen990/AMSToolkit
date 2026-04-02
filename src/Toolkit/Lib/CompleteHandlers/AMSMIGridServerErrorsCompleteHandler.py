import sys
import os
import re
from pydoc import locate

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from Toolkit.Config import AMSJibbixOptions
from Toolkit.Lib import AMSReturnCode
from Toolkit.Lib.CompleteHandlers import AbstractCompleteHandler


class AMSMIGridServerErrorsCompleteHandler(AbstractCompleteHandler):
    """
    This class will execute a command on the commandline and return the results.
    """

    def __init__(self, ams_config, ams_complete_handler):
        """
        :param ams_config:
        :type: AMSConfig
        :param ams_complete_handler:
        :type: AMSCompleteHandler
        """
        AbstractCompleteHandler.__init__(self, ams_config, ams_complete_handler)
        self.fev = FileExistsValidator()
        self.log_file = None

    def _run_complete_handler(self, schedule, is_success):
        """
        This method checks the specified directory and executes the touch command. Returns an AMSReturnCode object.
        :return: AMSReturnCode:
        """
        result = AMSReturnCode()
        result.job_success = True

        try:
            # Use default migs log if not configured
            # TODO: what about grabbing from the environment?
            if not self.AMSCompleteHandler.complete_handler:
                self.log_file = self.AMSConfig.AMSDefaults.default_migs_log
            else:
                self.log_file = self.AMSCompleteHandler.complete_handler.strip()

            self.AMSLogger.info('Checking grid server file %s' % self.log_file)

            description = ''
            reading_rpp = reading_mdo = False
            with open(self.log_file) as origin_file:
                for line in origin_file:
                    if reading_rpp:
                        if line.strip().startswith('Failure with DQ'):
                            reading_rpp = False
                            continue
                        else:
                            if re.findall(r'ERROR', line):
                                description += line
                                continue
                            else:
                                reading_rpp = False
                                continue
                    if reading_mdo:
                        if not line.strip():
                            reading_mdo = False
                            continue
                        else:
                            if re.findall(r'ERROR', line):
                                # skip this line
                                description += 'The following plans failed in batch opt/prep:' + os.linesep
                                continue
                            else:
                                description += line
                                continue

                    # Handle RPO errors
                    match = re.findall(r'ERROR: model group ', line)
                    if match:
                        # The string location is very specific to the grid log formatting
                        rindex = line.index('ERROR')
                        description += str(line[0:18] + ' ' + line[rindex:])

                    # Handle RPP errors
                    match = re.findall(r'INFO  -     ERROR: Plan_sk=', line)
                    if match:
                        # The string location is very specific to the grid log formatting
                        rindex = line.index('ERROR')
                        description += str(line[0:18] + ' ' + line[rindex:])
                        reading_rpp = True

                    # Handle MDO errors
                    match = re.findall(r'ERROR - Batch Opt/Prep failed', line)
                    if match:
                        # The string location is very specific to the grid log formatting
                        rindex = line.index('ERROR')
                        description += str(line[0:18] + ' ' + line[rindex:])
                        reading_mdo = True

            # Do jibbix stuff here
            add_comment_jibbix_options = locate('Toolkit.Config.AMSJibbixOptions')() # type: AMSJibbixOptions
            add_comment_jibbix_options.comment_only = 'true'
            add_comment_jibbix_options.link = 'comm'
            add_comment_jibbix_options.project = schedule.tla
            add_comment_jibbix_options.summary = 'No Summary (comment only)'

            event_handler = self.AMSConfig.ams_attribute_mapper.get_attribute('global_ams_event_handler')

            add_comment_jibbix_options.description = "%s:%s%s" % (self.AMSConfig.get_my_environment().env_type, os.linesep, os.linesep)
            if description:
                add_comment_jibbix_options.description += "Grid Server Errors:%s" % os.linesep
                add_comment_jibbix_options.description += description
            else:
                add_comment_jibbix_options.description += "No Grid Server Errors found"

            # Invoke the event handler with None as the schedule name so that the default toolkit.options zabbix item is used
            event_handler.create(add_comment_jibbix_options)

        except Exception as E:
            result.job_success = False
            result.add_error(str(E))

        return result

    def instructions_for_verification(self):
        return 'Verify the MI Grid logfile exists and can be read and written to: %s' % self.log_file
