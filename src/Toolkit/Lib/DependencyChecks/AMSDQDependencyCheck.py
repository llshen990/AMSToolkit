import sys
import os

from Toolkit.Lib.AMSReturnCode import AMSReturnCode
from lib.ETLFile import *
from lib.Exceptions import *


APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.DependencyChecks import AbstractAMSDependencyCheck

class AMSDQDependencyCheck(AbstractAMSDependencyCheck):

    def __init__(self,ams_config, ams_dependency_checker):
        """
       :param ams_config:
       :type:  AMSConfig
       :param ams_dependency_checker:
       :type: AMSDependencyChecker
       """
        AbstractAMSDependencyCheck.__init__(self, ams_config, ams_dependency_checker)
        self.dependency = self.AMSDependencyChecker.dependency.strip()
        self.descriptor_file = self.AMSDependencyChecker.descriptor_file.strip()
        self.debug = ams_config.debug
        self.instr = ''


    def _check_dependency(self):
        """
        This checks the dependency and returns true if it is successful and false otherwise.
        :return:
        :type: AMSReturnCode
        """

        res = False
        msg = "DQ Dependency check " + self.AMSDependencyChecker.dependency
        file_ret = None

        try:
            file_ret = File(self.dependency, self.descriptor_file, self.debug)
            if isinstance(file_ret,File):
                if file_ret.file_validated:
                    print('[SUCCESS] File passed validations.')
                    res = True
                    msg += " is successful"
                else:
                    msg += " is unsuccessful"
                    if file_ret.is_data_error():
                        for err in file_ret.errors:
                            self.instr += 'ERROR: '+ str(err)
        except StopBatchTriggerZabbixBatchDelayException as e:
            print('[ERROR] ' + str(e))
            msg += " is unsuccessful:" + os.linesep
            msg += str(e)
            self.instr = str(e)
        except SuccessfulStopValidationException as e:
            print('[SUCCESS] ' + str(e))
            res = True
            msg += " is successful"
        except (SkipValidationException, DuplicateRemovalSuccessException):
            res = True
            msg += " is successful"
        except Exception as e:
            print('[Error][Unknown] ' + str(e))
            msg += " is unsuccessful with exception: " + os.linesep
            msg += str(e)
            self.instr = str(e)
        return AMSReturnCode(self.AMSDependencyChecker.dependency, res, msg)

    def instructions_for_verification(self):
        ret_str = 'File %s should match the descriptor file %s ; %s' % (self.dependency, self.descriptor_file,os.linesep)
        if len(self.instr) == 0:
            ret_str += '{}Note: No issues found during DQ dependency check!{}'.format(os.linesep, os.linesep)
        else:
            ret_str += '{}Note: The following issues were found:{}'.format(os.linesep, os.linesep)
            ret_str += self.instr
        return ret_str

    def commandline_output(self):
        ret_str = 'File %s should match the descriptor file %s ; %s' % (self.dependency, self.descriptor_file, os.linesep)
        if len(self.instr) == 0:
            ret_str += '{}Note: No issues found during DQ dependency check!{}'.format(os.linesep, os.linesep)
        else:
            ret_str += '{}Note: The following issues were found:{}'.format(os.linesep, os.linesep)
            ret_str += self.instr
        return ret_str




