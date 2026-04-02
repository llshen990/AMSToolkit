import multiprocessing
from pathos import multiprocessing as mp
from os.path import join, islink
import re
import sys
import abc
import fnmatch
import os
import time
import scandir
import logging
import socket
import tarfile
import shutil

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Config import AMSFileHandler, AMSJibbixOptions, AMSConfig
from Toolkit.Exceptions import AMSFatalException, AMSValidationException
from Toolkit.Lib.Defaults import AMSDefaults
from lib.Validators import FileExistsValidator
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase

error_queue = multiprocessing.Queue()

class AMSFileHandler(AbstractAMSBase):
    __metaclass__ = abc.ABCMeta

    def __init__(self, ams_file_handler, ams_config):
        self.AMSLogger = logging.getLogger('AMS')
        self.AMSFileHandler = ams_file_handler  # type: AMSFileHandler
        self.AMSDefaults = AMSDefaults()
        self.fev = FileExistsValidator(debug=True)
        self.ErrorList = []
        self.file_age = 0 if self.AMSFileHandler.file_age is None else self.AMSFileHandler.file_age * 86400
        self.file_count = 0 if self.AMSFileHandler.file_count < 0 else self.AMSFileHandler.file_count
        self.current_time = int(time.time())
        self.ams_config = ams_config

    def evaluate_file_handler(self):
        try:
            self._search()
            errors = self.fev.get_errors() + self.ErrorList
            if errors:
                raise AMSValidationException('\n'.join(errors))
        except Exception as e:
            # Catch any errors encountered during eval.
            try:
                self.AMSLogger.error('Error encountered when running file handler {} attempting to create Jira'.format(
                    self.AMSFileHandler.file_handler_name))
                self._zabbix_send(e)
            except Exception as e2:
                self.AMSLogger.error('Unable to create Jira for file handler error, attempting email creation.\n{}'.format(str(e2)))
                try:
                    self._email_send(e)
                except Exception as e3:
                    self.AMSLogger.error('Failed to create Jira or send email for file parser error.\n{}\n{}'.format(str(e), str(e3)))

    def _email_send(self, e):
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        try:
            s = smtplib.SMTP('localhost')
        except:
            self.AMSLogger.error('Unable to connect to localhost for SMTP.')
            if os.path.exists('/etc/mail.rc'):
                with open('/etc/mail.rc', 'r') as mailfile:
                    mailserver = re.search('(set smtp=smtp://)(.*)', mailfile.read())
                s = smtplib.SMTP(mailserver.group(2))
            else:
                raise
        finally:
            try:
                msg = MIMEMultipart('alternative')
                msg['From'] = self.AMSDefaults.from_address
                msg['To'] = self.AMSDefaults.email_address
                msg['Subject'] = 'File Handler: "{}" has failed on host: {}'.format(self.AMSFileHandler, socket.gethostname())
                message = 'The file handler "{}" has failed on host {} with the following error\n{}'.format(
                    self.AMSFileHandler.file_handler_name, socket.gethostname(), str(e))
                msg.attach(MIMEText(message, 'plain'))
                s.sendmail(self.AMSDefaults.from_address, [msg['To']], msg.as_string())
            except Exception as givingup:
                self.AMSLogger.error('Despite our best efforts no notifications could be successfully sent.\n'
                                     'File Handler {} has failed.\n{}\n{}'.format(self.AMSFileHandler, str(e), str(givingup)))

    def _zabbix_send(self, e):
        from Toolkit.Lib.Helpers import AMSZabbix
        tmp_jibbix = self.AMSDefaults.AMSJibbixOptions
        tmp_jibbix.merge = 'yes'
        tmp_jibbix.summary = 'File Handler: "{}" has failed on host: {}'.format(
            self.AMSFileHandler.file_handler_name, socket.gethostname())
        tmp_jibbix.description = '\nHost: {}\nFile Handler: "{}"\nError: \n{}'.format(
            socket.gethostname(), self.AMSFileHandler.file_handler_name, str(e))
        event_handler = AMSZabbix(self.AMSLogger, self.ams_config)
        event_handler.call_zabbix_sender(self.AMSDefaults.default_zabbix_key_no_schedule,
                                         tmp_jibbix.str_from_options() + tmp_jibbix.description)

    def _match(self, path, name):
        self.AMSLogger.debug('Validating pattern=%s' % self.AMSFileHandler.file_pattern)
        if fnmatch.fnmatch(name, self.AMSFileHandler.file_pattern):
            creation_time = self.current_time + 1
            self.AMSLogger.debug('file=%s matches pattern=%s' % (os.path.join(path, name), self.AMSFileHandler.file_pattern))

            if self.AMSFileHandler.file_age is not None:
                creation_time = os.stat(path).st_mtime
            if (self.current_time - creation_time) >= self.file_age:
                try:
                    return True
                except IOError as io:
                    self.AMSLogger.error('File permission error encountered for {}'.format(name))
                    self.ErrorList.append(io)
                except Exception as e:
                    import traceback
                    self.AMSLogger.error("Caught an exception handling file file_name={}: {}".format(path, str(e)))
                    self.AMSLogger.error("Traceback: {}".format(traceback.format_exc()))
                    self.ErrorList.append(str(e))
            elif self.file_count > 0:
                self.AMSLogger.debug('file=%s does *NOT* match file age of %s days, pending...' % (os.path.join(path, name), self.AMSFileHandler.file_age))
                return True
            else:
                return False
        else:
            self.AMSLogger.debug('file=%s does *NOT* match pattern=%s' % (name, self.AMSFileHandler.file_pattern))
            return False

    def _search(self):
        root_dir = self.AMSFileHandler.directory_to_watch
        min_depth = self.AMSFileHandler.min_depth
        max_depth = float('inf') if self.AMSFileHandler.max_depth == -1 else self.AMSFileHandler.max_depth
        xlist = []

        if min_depth > max_depth:
            raise AMSValidationException('No Results: Min Depth ({}) > Max Depth ({})'.format(min_depth, max_depth))

        follow_symlinks = False
        if self.AMSFileHandler.follow_symlinks in ['Yes']:
            follow_symlinks = True

        try:
            self.AMSLogger.debug('Executing {} on {}'.format(self.AMSFileHandler.type, root_dir))
            for root, dirs, files, depth in AMSFileHandler.walk(root_dir, followlinks=follow_symlinks, onerror=self._log_error):
                try:
                    if min_depth <= depth <= max_depth:
                        if self.AMSFileHandler.level in ['Directory']:
                            removals = []
                            for directory in dirs:
                                path = os.path.join(root, directory)
                                match = self._match(path, directory)
                                if match:
                                    xlist.append((path, directory))
                                    removals.append(directory)
                            # Removing these within the above loop resulted in bizarre errors.
                            dirs[:] = [d for d in dirs if d not in removals]

                        elif self.AMSFileHandler.level in ['File']:
                            for file_name in files:
                                path = os.path.join(root, file_name)
                                if self._match(path, file_name):
                                    xlist.append((path, file_name))
                except Exception as e:
                    import traceback
                    self.AMSLogger.error("Caught an exception searching: {}".format(str(e)))
                    self.AMSLogger.error("Traceback: {}".format(traceback.format_exc()))
            if len(xlist) > max(0, self.file_count):
                xlist.sort(key=lambda f:os.stat(f[0]).st_mtime, reverse=True)
                try:
                    self._process_matches(xlist[self.file_count:])
                except IOError as io:
                    self.AMSLogger.error('File permission error encountered for {}'.format(xlist))
                    error_queue.put(io)
                except Exception as e:
                    self.AMSLogger.error('Error occurred while processing {}'.format(xlist))
                    error_queue.put(e)
        except Exception as e:
            raise AMSFatalException(str(e))

    def _process_matches(self, matches):
        pool = mp.Pool(4)
        if self.AMSFileHandler.type == 'Delete':
            handler = remove_source
        if self.AMSFileHandler.type == 'Compress':
            handler = compress_source
        if self.AMSFileHandler.type == 'Archive':
            handler = move_source
        for match in matches:
            self.AMSLogger.debug('Performing {} on {}'.format(self.AMSFileHandler.type, match[0]))
            pool.apply_async(handler, args=(match, self.AMSFileHandler.level, self.AMSFileHandler.archive_directory))
        pool.close()
        pool.join()
        while not error_queue.empty():
            file_in_error, message = error_queue.get()
            self.ErrorList.append(file_in_error)
            self.AMSLogger.error(message)

    def _log_error(self, error):
        self.AMSLogger.warning('File Handler "{}" has encountered a non-fatal file system issue.\n{}'.format(
            self.AMSFileHandler.file_handler_name, error))

    @staticmethod
    def walk(top, depth=0, onerror=None, followlinks=False):
        dirs = []
        nondirs = []

        # This is blatant grab of code for scandir.walk() which I have stripped and added depth as an arg.
        # It should likely be located somewhere else but I am putting it here for now.
        try:
            scandir_it = scandir.scandir(top)
        except OSError as error:
            if onerror is not None:
                onerror(error)
            return

        while True:
            try:
                try:
                    entry = next(scandir_it)
                except StopIteration:
                    break
            except OSError as error:
                if onerror is not None:
                    onerror(error)
                return

            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False

            if is_dir:
                dirs.append(entry.name)
            else:
                nondirs.append(entry.name)

        yield top, dirs, nondirs, depth

        # Recurse into sub-directories
        for name in dirs:
            new_path = join(top, name)
            if followlinks or not islink(new_path):
                for entry in AMSFileHandler.walk(new_path, depth+1, onerror, followlinks):
                    yield entry


def remove_source(current_path, level, archive_dir=None):
    current_path, _ = current_path
    if os.path.realpath(current_path) in ['/']:
        raise AMSFatalException("Unable to Delete Root Directory")

    try:
        abs_path_source_file = os.path.abspath(current_path)

        if level in ['File']:
            os.remove(abs_path_source_file)

        elif level in ['Directory']:
            shutil.rmtree(abs_path_source_file)

    except Exception as e:
        error_queue.put((current_path, 'Could not remove source file=%s with error=%s' % (current_path, str(e))))
        raise e # This exists merely for unit testing


def compress_source(current_path, level, archive_dir=None):
    current_path, _ = current_path
    resetdir = os.getcwd()
    source_dir = current_path
    source_file = ''
    try:
        while source_file == '':
            source_dir, source_file = os.path.split(source_dir)
        if os.path.splitext(source_file)[1] != '.gz':
            os.chdir(source_dir)
            with tarfile.open(source_file + ".tar.gz", "w:gz") as tar:
                tar.add(source_file)
            remove_source((current_path, None), level, archive_dir)
    except Exception as e:
        error_queue.put((current_path, "Could not compress source file=%s with error=%s" % (current_path, str(e))))
        raise e # This exists merely for unit testing
    finally:
        os.chdir(resetdir)


def move_source(current_path, level, archive_dir=None):
    current_path, match_name = current_path
    fev = FileExistsValidator()
    try:
        os.makedirs(archive_dir)
    except OSError as e:
        pass

    try:
        compress_source((current_path, match_name), level, archive_dir)
        compress_path = current_path + '.tar.gz'
        tgt_path = os.path.join(archive_dir, match_name + '.tar.gz')
        shutil.move(compress_path, tgt_path)

        if not fev.validate(tgt_path):
            fev.add_error(tgt_path, 'File has not been archived!')

    except Exception as e:
        error_queue.put((current_path, 'Could not archive source file=%s with error=%s' % (current_path, str(e))))
        raise e # This exists merely for unit testing
