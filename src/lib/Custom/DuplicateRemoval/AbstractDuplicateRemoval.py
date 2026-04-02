# @author owhoyt
import abc, os.path, sys, linecache, subprocess, ConfigParser, time, socket

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from lib.Exceptions import DuplicateRemovalException, DuplicateRemovalSuccessException
from lib.Helpers import ManifestCreate, EncryptPgP, SASEmail, Md5Sum
# noinspection PyUnresolvedReferences
from lib.Custom.Models import *
# from shutil import copyfile

class AbstractDuplicateRemoval(object):
    """This is the base duplicate removal class.  It is abstract and any implemented duplicate removal classes should extend
    this class to provide a standardized interface for calling and using any duplicate removers.

    Attributes:
        errors: A list of errors
        duplicates_found: A list of duplicates found
        orig_file: A list of errors
        new_file: A list of errors
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, debug=False):
        """ Instantiates an AbstractDuplicateRemoval object
        :param debug: bool
        :return: AbstractDuplicateRemoval
        """
        self.errors = []  # creates a new empty list for holding errors
        self.duplicates_found = []  # list of duplicates found
        self.orig_file = None  # path to orig. file
        self.new_file = None  # path to new file.
        self.debug = debug
        self.object_dict = {}
        self.strings_to_grep = []
        self.grep_string = ''
        self.data_object = None
        self.objects_to_remove = []
        self.grep_string_dup_remove = ''
        self.duplicate_removal_diff_report = ''
        self.md5_obj = Md5Sum()
        self.orig_md5 = None
        self.new_md5 = None
        self.duplicate_removal_routine_friendly_name = None

        # set some defaults / setup some config data
        self.config = ConfigParser.ConfigParser()
        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        self.config.read(os.path.abspath(abs_file_dir + '../../../../Config/ssod_validator.cfg'))
        self.backup_folder = ''
        if self.config.has_option('DEFAULT', 'automated_duplicate_removal_backup_location'):
            self.backup_folder = self.config.get('DEFAULT', 'automated_duplicate_removal_backup_location')
        else:
            raise DuplicateRemovalException('Could not __init__ AbstractDuplicateRemoval: Backup folder is not defined in the config.')

        self.debug = False
        if self.config.has_option('DEFAULT', 'debug'):
            self.debug = self.config.getboolean('DEFAULT', 'debug')

        self.final_backup_folder = None

    @abc.abstractmethod
    def _execute_remove_duplicates(self):
        """Required method to implement a duplicate removal class in order to remove duplicates.
        """
        return

    @abc.abstractmethod
    def set_new_data_object(self, data_object_str):
        return

    @abc.abstractmethod
    def generate_grep_string(self):
        return

    @abc.abstractmethod
    def generate_dup_remove_grep_string(self):
        return

    @abc.abstractmethod
    def set_duplicate_removal_routine_friendly_name(self, name):
        return

    @staticmethod
    def clear_linecache():
        linecache.clearcache()

    def get_new_data_object(self):
        if not self.data_object:
            raise DuplicateRemovalException('New data_object must be defined.')
        return globals()[self.data_object]()

    def get_line_from_file(self, line_number):
        line_number = int(line_number)
        return linecache.getline(self.orig_file, line_number)

    def remove_duplicates(self, raw_file, duplicates_found):
        """Required method to implement a duplicate removal class in order to remove duplicates.

        :type raw_file: string
        :param duplicates_found: list
        """
        self.orig_file = raw_file
        fev = FileExistsValidator(True)
        if not fev.validate(self.orig_file):
            raise DuplicateRemovalException('Duplicate exception: ' + fev.format_errors())
        self.duplicates_found = duplicates_found
        if not duplicates_found:
            print '[DUPLICATE ' + str(self) + '] no duplicates found, continuing'
            return True
        self.new_file = self.orig_file + '_duplicates_removed'
        try:
            # copyfile(self.orig_file, self.new_file)
            self.orig_md5 = self.md5_obj.md5_hash_for_file(self.orig_file)
            self._backup_orig_file()
            return self._execute_remove_duplicates()
        except (DuplicateRemovalException, DuplicateRemovalSuccessException):
            raise
        except Exception as e:
            raise DuplicateRemovalException(str(e))

    def _execute_dup_removal(self):
        if not self.grep_string_dup_remove or self.grep_string_dup_remove == '':
            raise DuplicateRemovalException('No duplicate string set to remove - please check your implementation of this duplicate removal')
        with open(self.new_file, 'w') as new_file_dupes_removed:
            grep_list = ['grep', '-v', self.grep_string_dup_remove, self.orig_file]
            grep = subprocess.Popen(grep_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            grep_std_out, grep_std_err = grep.communicate()
            if grep_std_err:
                raise DuplicateRemovalException('Error in find_supp_act(): ' + grep_std_err.strip())

            new_file_dupes_removed.write(grep_std_out)
        new_file_dupes_removed.close()

        self.new_md5 = self.md5_obj.md5_hash_for_file(self.new_file)
        # compare the md5 hashes, if they are differnt, do the below, otherwise, skip - all is good
        if self.orig_md5 != self.new_md5:
            self._print_msg('Creating Diff Report')
            # create a diff report to log any differences from orig file w/o null bytes and encoded file with target encoding
            self._get_file_diff()

            # create the exception report / email
            self._print_msg('Creating Exception Report Email')
            self._create_exception_report()

            # replace the orig file w/ the temp file:
            self._print_msg('Replacing orig. file with newly encoded file')
            self._replace_file_with_tmp_file()

            self._print_msg('creating new manifest file')
            # create the new manifest file
            self.create_new_manifest()

            self._print_msg('encrypting new file')
            # re-encrypt the new file:
            self.encrypt_file()

            print '[DUPLICATE ' + str(self) + '] ' + str(len(self.objects_to_remove)) + ' records have been removed.  The file will be re-validated on the next run of the DQ package.'
            raise DuplicateRemovalSuccessException('Successfully removed duplicates, re-queuing file for validation.')
        else:
            raise DuplicateRemovalException('Duplicate removal process has run, but the newly created file without duplicates is the same as the original file.  Please investigate.')

    def _replace_file_with_tmp_file(self):
        file_validator = FileExistsValidator(True)
        if not (file_validator.validate(self.new_file)):
            raise DuplicateRemovalException('Exception in _replace_file_with_tmp_file: File ' + self.new_file + ' does not exist')

        pm2 = subprocess.Popen(['mv', self.new_file, self.orig_file])
        pm2.wait()

    def _backup_orig_file(self):
        if not self.backup_folder:
            raise DuplicateRemovalException('Exception in replace_file(backup_file): Config File does not have a backup location specified')

        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)

        time_stamped_folder = self.backup_folder + '/' + (time.strftime('%Y%m%d_%H%M'))
        if not os.path.exists(time_stamped_folder):
            os.makedirs(time_stamped_folder)

        # move the orig file / manifest to the backup location
        self._print_msg('Backing up orig files to: ' + time_stamped_folder)
        pm = subprocess.Popen('cp ' + self.orig_file.replace('file', '*') + '.* ' + time_stamped_folder, shell=True)
        pm.wait()

        self.final_backup_folder = time_stamped_folder
        return True

    def _get_file_diff(self):
        p = subprocess.Popen(["diff", '--unified=0', self.orig_file, self.new_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        diff_std_out, diff_std_err = p.communicate()
        if diff_std_out or diff_std_err:
            self.duplicate_removal_diff_report += os.linesep + "------------------[DIFF REPORT] ---------------" + os.linesep
            self.duplicate_removal_diff_report += diff_std_out
            self.duplicate_removal_diff_report += diff_std_err

    def _create_exception_report(self):
        exception_email_addresses = None
        exception_report_dir = None
        exception_report_dir_outgoing = None

        if self.config.has_option('DEFAULT', 'exception_report_emails'):
            exception_email_addresses = self.config.get('DEFAULT', 'exception_report_emails')

        if self.config.has_option('DEFAULT', 'exception_report_dir'):
            exception_report_dir = self.config.get('DEFAULT', 'exception_report_dir')
            if not os.path.exists(exception_report_dir):
                os.makedirs(exception_report_dir)

        if self.config.has_option('DEFAULT', 'exception_report_dir_outgoing'):
            exception_report_dir_outgoing = self.config.get('DEFAULT', 'exception_report_dir_outgoing')

        if not exception_email_addresses and (not exception_report_dir or not exception_report_dir_outgoing):
            raise DuplicateRemovalException('Exception in _create_exception_report: config does not have proper config options: not exception_email_addresses and (not exception_report_dir or not exception_report_dir_outgoing)')

        exception_file_name = os.path.basename(self.orig_file) + '_duplicate_removal_report.txt'
        if exception_report_dir:
            with open(exception_report_dir + '/' + exception_file_name, 'w') as exception_rpt:
                exception_rpt.write(self.duplicate_removal_diff_report)

        if exception_report_dir_outgoing:
            with open(exception_report_dir_outgoing + '/' + exception_file_name, 'w') as exception_rpt:
                exception_rpt.write(self.duplicate_removal_diff_report)

        exception_email_msg = 'Hello,<br /><br />'
        exception_email_msg += 'SAS has automatically applied a duplicate removal routine (' + self.duplicate_removal_routine_friendly_name + ') to file: ' + os.path.basename(self.orig_file) + '.  '
        exception_email_msg += 'The original file(s) have been backed up to: ' + self.final_backup_folder + '<br /><br />'
        exception_email_msg += str(len(self.objects_to_remove)) + ' records have been removed.  The file will be re-validated on the next run of the DQ package.<br />'
        exception_email_msg += "<br />"

        if exception_report_dir_outgoing:
            exception_email_msg += 'A copy of the exception report has been placed in the outgoing folder and is named: ' + exception_file_name
        exception_email_msg += '<br /><br />'

        exception_email_msg += 'Thank You,<br />'
        exception_email_msg += 'Team SSOD'

        hostname = str(socket.gethostname()).strip()
        environment = 'UKN'
        if self.config.has_option('ENV_HOSTNAME_LOOKUP', hostname):
            environment = self.config.get('ENV_HOSTNAME_LOOKUP', hostname)
        sas_email = SASEmail()
        sas_email.set_from('replies-disabled@sas.com')
        sas_email.set_to(exception_email_addresses)
        sas_email.set_subject("[" + self.config.get('DEFAULT', 'market_config_section') + ' ' + environment + ': ' + hostname + "]" + self.duplicate_removal_routine_friendly_name)
        sas_email.set_text_message(exception_email_msg)
        sas_email.send()

    def create_new_manifest(self):
        manifest_create = ManifestCreate(self.orig_file)
        manifest_create.create_manifest()

    def encrypt_file(self):
        encrypt = EncryptPgP(self.orig_file)
        encrypt.encrypt()

    def add_error(self, data_input, error_message):
        """Adds an error message to the internal errors list in order to keep track of all errors.

        :type error_message: str
        :type data_input: str
        :param data_input: value of data input that triggered error
        :param error_message: Error message
        :return bool
        """
        if self.debug:
            self.errors.append(" '" + data_input + "' " + error_message)
        else:
            self.errors.append(" " + error_message)

        return True

    def get_errors(self):
        """ This method will return the list of errors

        :return: list
        """
        return self.errors

    def format_errors(self):
        """ This method will take all errors, if any, and return a formatted string of the errors

        :return: str
        """
        if len(self.errors) == 0:
            return ""
        return os.linesep.join(self.errors)

    def reset_errors(self):
        """ This method will reset the error list.
        Returns: Bool
        """
        self.errors = []
        return True

    def _print_msg(self, msg):
        if self.debug:
            print str(msg)

    def __str__(self):
        """magic method when you call print({my duplicate removal class}) to print the name of the duplicate removal class"""
        return self.__class__.__name__

    def __del__(self):
        """This is the destructor for DecryptPgP.  It will shred the file i.e. securely delete it."""
        file_validator = FileExistsValidator(True)
        if file_validator.validate(self.new_file):
            from lib.Helpers import FileShredder
            FileShredder(self.new_file)
        return