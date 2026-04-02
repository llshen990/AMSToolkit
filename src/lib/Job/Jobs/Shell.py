import os.path
import re
import subprocess
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from lib.Job.AbstractJob import AbstractJob
from lib.Exceptions import JobException
from lib.Helpers import OutputFormatHelper
import traceback

class Shell(AbstractJob):
    """
    This class houses functionality for executing a shell JOB (i.e. bash or some other shell command).
    It is important that ALL scripts that you call have a proper shebang line where appropriate (shell etc).
    In addition, it must 'exit' a shell script and not 'return'.  
    
    if [[ "${BASH_SOURCE[0]}" != "${0}" ]]
    then
        echo "runAMLJob.sh return code=$rval"
        return $rval
    else
        echo "runAMLJob.sh exit code=$rval"
        exit $rval
    fi
    
    """
    def __init__(self, script_path, sig_path, debug=False, preq_sig=None):
        AbstractJob.__init__(self, sig_path, debug, preq_sig)
        # get config options
        script_path = str(script_path).strip()
        if not self.file_exists_validator.validate(script_path):
            raise JobException('[INVALID_JOB] Script does not exist: ' + script_path)

        if not self.file_exists_validator.is_exe(script_path):
            raise JobException('[INVALID_JOB] Script does not have executable property set: ' + script_path)

        self.script_path = script_path
        self.return_code = None  # type: int
        self.std_out = None  # type: str
        self.std_err = None  # type: str
        self.error_pattern_list = ["ERROR", "Failure", "Permission denied"]

    def detect_error(self):
        """
        This method will detect errors in the job unless an exception occurrs.
        :return:
        :rtype:
        """
        self.job_success = True
        if self.std_err != "":
            self.add_error('There was an error running this job (std_error output): ' + str(self.std_err))
            self.job_error = True
            self.job_success = False

        if self.return_code > 0:
            self.add_error('There was an error running this job (return_code > 0): ' + str(self.return_code))
            self.job_error = True
            self.job_success = False

        pattern = re.compile('|'.join(self.error_pattern_list))
        errors = pattern.findall(self.std_out)
        if len(errors) > 0:
            self.add_error('There was an error running this job (std_out output): ' + str(self.std_out))
            self.job_error = True
            self.job_success = False

        return True

    def run_job(self):
        """
        This overriding method contains the logic for running a job.
        """
        try:
            self.log_it('In run_job for ' + str(self))
            process_args = [self.script_path]
            process_args.extend(self.attribute_ary)

            p = subprocess.Popen(process_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
            self.std_out, self.std_err = p.communicate()
            self.std_out = self.std_out.strip()
            self.std_err = self.std_err.strip()
            self.return_code = p.returncode

            self.log_it('results from: ' + self.script_path + ' ' + OutputFormatHelper.join_output_from_list(self.attribute_ary, ' '))
            self.log_it('std_out: ' + str(self.std_out))
            self.log_it('return_code: ' + str(self.return_code))
        except Exception as e:
            self.add_error('Caught exception running job: ' + str(e))
            self.add_error(traceback.format_exc())

    def get_job_name(self):
        return str(self) + ' - ' + os.path.basename(self.script_path) + " " + " ".join(self.attribute_ary)
