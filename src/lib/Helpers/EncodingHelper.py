#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path, sys, subprocess, ConfigParser, codecs, socket, time

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator, CharsetValidator
from lib.Exceptions import EncodingException
from lib.Helpers import ManifestCreate, EncryptPgP, SASEmail, Md5Sum

class EncodingHelper(object):
    """
    EncodingHelper houses all functionality with respect to file encoding and manages the conversion, reporting and feedback of the encoding conversion.
    Attributes:
        backup_folder: folder for which the orig. files are backed up.
        config: ConfigParser object of global configs.
        conversion_exceptions: houses a string of the conversion changes
        converted_file_tmp: Temporary copy of the converted file.
        file: Input file to check / convert encoding.
        from_encoding: the encoding passed into convert_file_encoding in order to convert the file.
        rawEncoding: Holds the orig, unchanged encoding of source file AFTER replacing null bytes.
        origEncoding: Holds the orig, unchanged encoding of source file without any modification of file
        to_encoding: The encoding to which we're trying to convert the file.
        translatedEncoding: The orig. encoding of the source file as interpreted by file -bi with a //TRANSLIT option added
        has_null_bytes: bool - whether or not the file has null bytes detected
        orig_md5: holds the md5 of the orig file
        replaced_md5: holds the md5 of the resultant file
        has_external_orig_file_backup: a backup of the orig. file was complete by an external utility
        from_encoding_if_error: If the automatic encoding from resolves to unknown, use this encoding instead of default
    """

    def __init__(self, input_file):
        try:
            input_file = str(input_file).strip()
            self.file = os.path.abspath((os.path.dirname(input_file.rstrip(os.pathsep)) or '.')) + '/' + os.path.basename(input_file)

            file_validator = FileExistsValidator(True)
            if not (file_validator.validate(self.file)):
                raise EncodingException('Could not __init__ EncodingHelper: File ' + input_file + ' does not exist')

            self.origEncoding = self.determine_file_encoding()
            self.rawEncoding = None
            self.translatedEncoding = None

            self.converted_file_tmp = self.file + '_converted'
            self.converted_file = None
            self.conversion_exceptions = ''
            self.md5_obj = Md5Sum()
            self.orig_md5 = self.md5_obj.md5_hash_for_file(self.file)
            self.replaced_md5 = None

            # set some defaults / setup some config data
            self.config = ConfigParser.ConfigParser()
            abs_file_dir = os.path.abspath(os.path.dirname(__file__))
            self.config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
            self.backup_folder = ''
            if self.config.has_option('DEFAULT', 'orig_file_backup_location'):
                self.backup_folder = self.config.get('DEFAULT', 'orig_file_backup_location')
            else:
                raise EncodingException('Could not __init__ EncodingHelper: Backup folder is not defined in the config.')

            self.debug = False
            if self.config.has_option('DEFAULT', 'debug'):
                self.debug = self.config.getboolean('DEFAULT', 'debug')

            self.to_encoding = None
            self.from_encoding = None
            self.has_null_bytes = False
            self.has_external_orig_file_backup = False
            self.no_diff_report = False
            self.no_manifest = False
            self.no_encrypt = False
            self.custom_msg = None
            self.final_backup_folder = None
            self.from_encoding_if_error = []
        except Exception as e:
            raise EncodingException('Caught Exception __init__: ' + str(e))

    def get_current_encoding(self, raw_encoding=True):
        if raw_encoding:
            return self.rawEncoding
        return self.translatedEncoding

    def determine_file_encoding(self, file_name=None):
        if not file_name:
            file_name = self.file
        else:
            file_validator = FileExistsValidator(True)
            if not (file_validator.validate(file_name)):
                raise EncodingException('Could not __init__ EncodingHelper: File ' + file_name + ' does not exist')

        return str(os.popen("file -bi " + file_name + " | sed -e 's/.*[ ]charset=//'").read()).strip()

    def convert_file_encoding(self, to_encoding, from_encoding=None, from_encoding_if_automatic_unknown='', from_encoding_if_error=None):
        if from_encoding_if_error and len(from_encoding_if_error) > 0:
            self.from_encoding_if_error = from_encoding_if_error

        # 1st make a backup of the orig file:
        self.backup_orig_file()

        # store the 'to encoding'
        self.to_encoding = str(to_encoding).strip()

        # check file for null bytes.
        if self.origEncoding != 'utf-16le':
            self.detect_null_bytes()

        # replace null bytes
        if self.has_null_bytes:
            self._print_msg('NULL Bytes detected - removing and logging to exception')
            null_subprocess_cmds = list()
            null_subprocess_cmds.append("tr")
            null_subprocess_cmds.append("-d")
            null_subprocess_cmds.append("\\000")
            with open(self.converted_file_tmp, 'w') as converted_file_output:
                npp = subprocess.Popen(null_subprocess_cmds, stdin=open(self.file), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                null_std_out, null_std_error = npp.communicate()
                converted_file_output.write(null_std_out)
            converted_file_output.close()

            # replace the orig. file with the tmp file cleaned of null bytes
            self.replace_file_with_tmp_file()

        # get the encoding of the file after null bytes are stripped
        self.rawEncoding = self.determine_file_encoding()
        self.translatedEncoding = self.rawEncoding

        # do a bit of transformation of unknown charsets
        if self.translatedEncoding in ["unknown-8bit", "binary"]:
            if from_encoding_if_automatic_unknown:
                self.translatedEncoding = from_encoding_if_automatic_unknown
            else:
                raise EncodingException('Unsupported from encoding: ' + self.translatedEncoding + '.  Cannot automatically validate this file due to invalid source file encoding.')

        # if a from encoding override is not sent in, use the auto detection
        if not from_encoding:
            self.from_encoding = self.translatedEncoding
        else:
            self.from_encoding = from_encoding

        # validate the charsets are usable / available with iconv
        charset_validator = CharsetValidator(True)
        if not (charset_validator.validate(self.to_encoding)):
            raise EncodingException('Exception in convert_file_encoding(to_encoding): ' + self.to_encoding + ' is not a valid charset')

        if not (charset_validator.validate(self.from_encoding)):
            raise EncodingException('Exception in convert_file_encoding(from_encoding): ' + self.from_encoding + ' is not a valid charset')

        # self.translatedEncoding += '//TRANSLIT'
        # self.from_encoding += '//TRANSLIT'
        # self.to_encoding += '//TRANSLIT'

        # perform the iconv encoding translation using the orig. file path as input and tmp file as output
        self._iconv_conversion()

        # after the encoding conversion, compute the md5 of the tmp file.
        self.replaced_md5 = self.md5_obj.md5_hash_for_file(self.converted_file_tmp)

        # compare the md5 hashes, if they are differnt, do the below, otherwise, skip - all is good
        if self.orig_md5 != self.replaced_md5:
            if not self.no_diff_report:
                self._print_msg('Creating Diff Report')
                # create a diff report to log any differences from orig file w/o null bytes and encoded file with target encoding
                self._get_file_diff()

            # create the exception report / email
            self._print_msg('Creating Exception Report Email')
            self._create_exception_report()

            # replace the orig file w/ the temp file:
            self._print_msg('Replacing orig. file with newly encoded file')
            self.replace_file_with_tmp_file()

            if not self.no_manifest:
                self._print_msg('creating new manifest file')
                # create the new manifest file
                self.create_new_manifest()

            if not self.no_encrypt:
                self._print_msg('encrypting new file')
                # re-encrypt the new file:
                self.encrypt_file()
        else:
            self._print_msg('Files do not differ, no null bytes removed / encoding did not change data')

    def _iconv_conversion(self):
        self._print_msg('Iconv - From: ' + self.from_encoding + ' To: ' + self.to_encoding)
        subprocess_cmds = list()
        subprocess_cmds.append("iconv")
        subprocess_cmds.append("-f")
        subprocess_cmds.append(self.from_encoding)
        # subprocess_cmds.append("-c")
        subprocess_cmds.append("-t")
        subprocess_cmds.append(self.to_encoding)
        subprocess_cmds.append(self.file)

        with open(self.converted_file_tmp, 'w') as converted_file_output:
            p = subprocess.Popen(subprocess_cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # self.converted_file = os.system("iconv -f " + self.from_encoding + " -t " + self.to_encoding + " " + self.file + " > " + self.file + '_converted')
            tmp_iconv_std_out, tmp_iconv_std_err = p.communicate()
            self._print_msg('tmp_iconv_std_err: ' + tmp_iconv_std_err)
            if tmp_iconv_std_err:
                self._print_msg('There is an error with the conversion, and we have ' + str(len(self.from_encoding_if_error)) + ' and these options: ' + str(self.from_encoding_if_error))
                self.conversion_exceptions += tmp_iconv_std_err
                if self.from_encoding_if_error and len(self.from_encoding_if_error) > 0:
                    self.from_encoding = self.from_encoding_if_error.pop(0)
                    self._print_msg('Trying new from encoding: ' + self.from_encoding)
                    converted_file_output.close()
                    return self._iconv_conversion()
                else:
                    converted_file_output.close()
                    raise EncodingException('Error encountered when trying to convert from ' + self.from_encoding + ' --> ' + self.to_encoding + '.')

            if self.to_encoding == 'UTF-8':
                converted_file_output.write(tmp_iconv_std_out.strip(codecs.BOM_UTF8))
            else:
                converted_file_output.write(tmp_iconv_std_out)

        converted_file_output.close()

    def replace_file_with_tmp_file(self):
        file_validator = FileExistsValidator(True)
        if not (file_validator.validate(self.converted_file_tmp)):
            raise EncodingException('Exception in replace_file_with_tmp_file: File ' + self.converted_file_tmp + ' does not exist')

        pm2 = subprocess.Popen(['mv', self.converted_file_tmp, self.file])
        pm2.wait()

    def create_new_manifest(self):
        manifest_create = ManifestCreate(self.file)
        manifest_create.create_manifest()

    def encrypt_file(self):
        encrypt = EncryptPgP(self.file)
        encrypt.encrypt()

    def set_has_external_orig_file_backup(self):
        self.has_external_orig_file_backup = True

    def set_no_diff_report(self):
        self.no_diff_report = True

    def set_no_manifest(self):
        self.no_manifest = True

    def set_no_encrypt(self):
        self.no_encrypt = True

    def set_custom_email_msg(self, custom_msg):
        self.custom_msg = custom_msg.strip() + '<br /><br />'

    def set_final_backup_folder(self, backup_folder):
        self.final_backup_folder = str(backup_folder).strip()

    def backup_orig_file(self):
        if self.has_external_orig_file_backup:
            return

        if not self.backup_folder:
            raise EncodingException('Exception in replace_file(backup_file): Config File does not have a backup location specified')

        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)

        time_stamped_folder = self.backup_folder + '/' + (time.strftime('%Y%m%d_%H%M'))
        if not os.path.exists(time_stamped_folder):
            os.makedirs(time_stamped_folder)

        # move the orig file / manifest to the backup location
        self._print_msg('Backing up orig files to: ' + time_stamped_folder)
        pm = subprocess.Popen('cp ' + self.file.replace('file', '*') + '.* ' + time_stamped_folder, shell=True)
        pm.wait()

        self.final_backup_folder = time_stamped_folder

    def detect_null_bytes(self):
        self._print_msg('Detecting null bytes...')
        subprocess_cmds = list()
        subprocess_cmds.append("grep")
        subprocess_cmds.append("-Pa")
        subprocess_cmds.append("\\x00")
        subprocess_cmds.append(self.file)
        p = subprocess.Popen(subprocess_cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        std_out, std_err = p.communicate()
        if std_out:
            self.conversion_exceptions += os.linesep + "------------------[NULL BYTES FOUND IN BELOW LINES]---------------------" + os.linesep
            self.conversion_exceptions += std_out
            self.has_null_bytes = True

        if std_err:
            self.conversion_exceptions += os.linesep + "------------------[ERRORS DETECTED BELOW WHEN SEARCHING FOR NULL BYTES] ---------------" + os.linesep
            self.conversion_exceptions += std_err
            raise EncodingException('Exception in replace_null_bytes(std_error): ' + str(std_err))

        return self.has_null_bytes

    def _get_file_diff(self):
        p = subprocess.Popen(["diff", '--unified=0', self.file, self.converted_file_tmp], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        diff_std_out, diff_std_err = p.communicate()
        if diff_std_out or diff_std_err:
            self.conversion_exceptions += os.linesep + "------------------[DIFF REPORT] ---------------" + os.linesep
            self.conversion_exceptions += diff_std_out
            self.conversion_exceptions += diff_std_err

    def get_encoded_filename(self):
        return self.file

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
            raise EncodingException('Exception in _create_exception_report: config does not have proper config options: not exception_email_addresses and (not exception_report_dir or not exception_report_dir_outgoing)')

        exception_file_name = None
        if not self.no_diff_report:
            exception_file_name = os.path.basename(self.file) + '_encoding_conversion_error.txt'
            if exception_report_dir:
                with open(exception_report_dir + '/' + exception_file_name, 'w') as exception_rpt:
                    exception_rpt.write(self.conversion_exceptions)

            if exception_report_dir_outgoing:
                with open(exception_report_dir_outgoing + '/' + exception_file_name, 'w') as exception_rpt:
                    exception_rpt.write(self.conversion_exceptions)

        exception_email_msg = 'Hello,<br /><br />'
        exception_email_msg += 'SAS has automatically applied an encoding fix-up to the file: ' + os.path.basename(self.file) + '.  '
        exception_email_msg += 'The original file(s) have been backed up to: ' + self.final_backup_folder + '<br /><br />'
        exception_email_msg += 'FROM: ' + self.from_encoding + "<br />"
        exception_email_msg += 'TO: ' + self.to_encoding + "<br />"
        if self.to_encoding.lower().strip('-') == self.from_encoding.lower().strip('-') and not self.has_null_bytes:
            exception_email_msg += "Note: The 'To' encoding is a 'best guess' and the conversion to the 'From' encoding may have properly transformed or discarded some characters."
        else:
            exception_email_msg += "<br />"

        if self.has_null_bytes:
            exception_email_msg += 'SAS has automatically removed some \'null bytes\' from the file: ' + os.path.basename(self.file) + '<br /><br />'

        if not self.no_diff_report:
            if exception_report_dir_outgoing:
                exception_email_msg += 'A copy of the exception report has been placed in the outgoing folder and is named: ' + exception_file_name
            exception_email_msg += '<br /><br />'

        if self.custom_msg:
            exception_email_msg += self.custom_msg

        exception_email_msg += 'Thank You,<br />'
        exception_email_msg += 'Team SSOD'

        hostname = str(socket.gethostname()).strip()
        environment = 'UNKNOWN SERVER'
        if self.config.has_option('ENV_HOSTNAME_LOOKUP', hostname):
            environment = self.config.get('ENV_HOSTNAME_LOOKUP', hostname)
        sas_email = SASEmail()
        sas_email.set_from('replies-disabled@sas.com')
        sas_email.set_to(exception_email_addresses)
        sas_email.set_subject("[" + self.config.get('DEFAULT', 'market_config_section') + ' ' + environment + ': ' + hostname + "] Encoding Exception")
        sas_email.set_text_message(exception_email_msg)
        sas_email.send()

    def _print_msg(self, msg):
        if self.debug:
            print str(msg)

    def __del__(self):
        """This is the destructor for EncodingHelper.  It will shred the temp file i.e. securely delete it."""
        file_validator = FileExistsValidator(True)
        if file_validator.validate(self.converted_file_tmp):
            from lib.Helpers import FileShredder
            FileShredder(self.converted_file_tmp)