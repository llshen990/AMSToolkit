import re
import os
import time
import smtplib
import scandir
import pickle
import logging
import subprocess
from stat import *
from fnmatch import fnmatch
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from Toolkit.Config import AMSFileParser
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from Toolkit.Lib.Helpers import AMSTouch, AMSFile, AMSZabbix
from Toolkit.Lib.Defaults import AMSDefaults

# Seconds Per Day
SECPERDAY = 86400

class AMSFileParser(AbstractAMSBase):

    def __init__(self, ams_config, parser_name):
        self.logger = logging.getLogger('AMS')
        self.ams_config = ams_config
        self.ams_config_dir = ams_config.config_path
        self.parser_config = ams_config.get_file_parser_by_name(parser_name)
        self.records = {}
        self.pattern = re.compile(self.parser_config.search_pattern)
        try:
            self.exclude_pattern_joined = '|'.join([x.strip() for x in self.parser_config.exclude_pattern.split(",")])
            self.exclusion_pattern = re.compile(self.exclude_pattern_joined)
        except:
            self.exclude_pattern_joined = None
        self.index_file = None
        self.current_time = time.time()

    def evaluate_file_parser(self):
        min_depth = self.parser_config.min_depth
        max_depth = float('inf') if self.parser_config.max_depth < 0 else self.parser_config.max_depth
        parser_filename = self._get_valid_filename(self.parser_config.file_parser_name)
        self.logger.debug('Starting AMSFileParser ({}) in {}'.format(parser_filename, self.parser_config.base_directory))
        match_collector = {}
        self.index_file = self._find_index_file(self.parser_config.base_directory, parser_filename)

        self._load_index_file()

        for root, dirs, files, depth in AMSFileParser.walk(self.parser_config.base_directory):
            if min_depth <= depth < max_depth:
                file_pattern_list = [x.strip() for x in self.parser_config.file_pattern.split(",")]
                for pattern in file_pattern_list:
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        if fnmatch(file_name, pattern) and self._check_file_age(file_path):
                            tmp_matches = self._parse_file(file_path)
                            if tmp_matches != {}:
                                self.logger.debug('AMSFileParser ({}) found matches in {}'.format(
                                    self.parser_config.file_parser_name, file_path))
                                match_collector[file_path] = tmp_matches
        self._write_records(self.index_file)
        if match_collector != {}:
            self._action_records(match_collector)

    def _action_records(self, match_collection):
        self.logger.debug('AMSFileParser ({}) is attempting {} action for matches.'.format(
            self.parser_config.file_parser_name, self.parser_config.on_match_actions))
        try:
            if self.parser_config.on_match_actions == 'TouchFile':
                self._touch_file(self.parser_config.touch_file)
            elif self.parser_config.on_match_actions == 'ClearSignal':
                self._clear_sig(self.parser_config.clear_signal)
            elif self.parser_config.on_match_actions == 'Script':
                self._run_script(self.parser_config.script)
            elif self.parser_config.on_match_actions == 'Email':
                self._email_send(match_collection)
            elif self.parser_config.on_match_actions == 'Zabbix':
                self._zabbix_send(match_collection)
        except Exception as e:
            self.logger.critical('AMSFileParser was unable to action records\n{}'.format(str(e)))

    def _email_send(self, match_collection):
        try:
            s = smtplib.SMTP('localhost')
            msg = MIMEMultipart('alternative')
            msg['From'] = AMSDefaults().from_address
            msg['To'] = self.parser_config.parser_email_address

            message = ['The file parser "{}" found the following matches for the regex pattern "{}":\n'.format(
                self.parser_config.file_parser_name, self.parser_config.search_pattern)]
            for file_name in match_collection.keys():
                message.append('Filename: {}'.format(file_name))
                for byte_offset, match in sorted(match_collection[file_name].items()):
                    if self.parser_config.confidential_action:
                        match['line'] = 'REDACTED'
                    message.append('\tLine #{}: "{}"'.format(match['line_number'], match['line']))
            if self.parser_config.AMSJibbixOptions.summary:
                msg['SUBJECT'] = self.parser_config.AMSJibbixOptions.summary
            else:
                msg['SUBJECT'] = 'File parser "{}" detected matches on host {}'.format(
                    self.parser_config.file_parser_name, self.parser_config.my_hostname)
            #Exclude pattern
            if self.parser_config.exclude_pattern:
                message.append('\nLines containing the following regex pattern(s) were excluded: "{}"'.format(self.parser_config.exclude_pattern))

            msg.attach(MIMEText('\n'.join(message), 'plain'))
            s.sendmail('replies-disabled@sas.com', self.parser_config.parser_email_address.split(','), msg.as_string())
        except Exception as e:
            self.logger.error('Unexpected exception when sending mail notification for parser {}: {}'.format(
                self.parser_config.file_parser_name, str(e)))
        finally:
            s.quit()

    def _zabbix_send(self, match_collection):
        ams_defaults = AMSDefaults()
        zabbix_handler = AMSZabbix(self.logger, config=self.ams_config, hostname=self.parser_config.my_hostname)
        if self.parser_config.AMSJibbixOptions.summary == '':
            self.parser_config.AMSJibbixOptions.summary = 'Parser match detected for parser: {} on host: {}'.format(
                self.parser_config.file_parser_name, self.parser_config.my_hostname)
        message = [self.parser_config.AMSJibbixOptions.str_from_options(),
                   '\nThe file parser "{}" found the following matches for the regex pattern "{}":\n'.format(
                       self.parser_config.file_parser_name, self.parser_config.search_pattern)]
        for file_name in match_collection.keys():
            message.append('Filename: {}'.format(file_name))
            for byte_offset, match in sorted(match_collection[file_name].items()):
                if self.parser_config.confidential_action:
                    match['line'] = 'REDACTED'
                message.append('\tLine #{}: "{}"'.format(match['line_number'], match['line']))
        message.append('\nRunbook link: {}\nSummary: {}'.format(self.ams_config.runbook_link, self.parser_config.AMSJibbixOptions.summary))
        result = zabbix_handler.call_zabbix_sender(ams_defaults.default_zabbix_key_no_schedule, '\n'.join(message))
        if not result:
            self.logger.error('Zabbix send failed for file parser: {}'.format(self.parser_config.file_parser_name))

    def _run_script(self, script):
        try:
            p = subprocess.check_output(script, stderr=subprocess.STDOUT)
            self.logger.info('Parser on action script returned the following STDOUT/STDERR: {} for parser: {}'.format(
                p.strip(), self.parser_config.file_parser_name))
        except subprocess.CalledProcessError:
            self.logger.error('Parser on action script returned a non-zero exit status for parser: {}'.format(
                self.parser_config.file_parser_name))
        except Exception as e:
            self.logger.error('Something went wrong when attempting to execute {} as a parser on action script for parser: {}'.format(
                script, self.parser_config.file_parser_name))

    def _clear_sig(self, file_path):
        try:
            AMSFile.remove(file_path)
        except Exception as e:
            self.logger.error('Failed to remove signal file: {} as a parser action for parser: {}. The following '
                              'error was returned: {}'.format(file_path, self.parser_config.file_parser_name, str(e)))

    def _touch_file(self, file_path):
        try:
            AMSTouch.touch(file_path)
            self.logger.info('Touch file created at: {}'.format(file_path))
        except Exception as e:
            self.logger.error('Failed to create touch file: {} as a parser action for parser: {}. The following '
                              'error was returned: {}'.format(file_path, self.parser_config.file_parser_name, str(e)))

    def _parse_file(self, file_path):
        line_offset = 1
        file_matches = {}
        if file_path not in self.records.keys():
            self.records[file_path] = {}
        matches = self.records[file_path]
        try:
            with open(file_path, 'rb') as file_to_parse:
                if len(matches.keys()) > 0:
                    last_index = sorted(matches.keys())[-1]
                    last_line = matches[last_index]['line']
                    line_offset = matches[last_index]['line_number'] + 1
                    file_to_parse.seek(last_index)
                    if file_to_parse.readline().strip() != last_line:
                        line_offset = 1
                        file_to_parse.seek(0, 0)
                        self.records[file_path] = {}
                        self.logger.debug('The current file matches in name but the index mismatches so we will '
                                          'restart parsing from the beginning. Filename: {}'.format(file_path))
                while True:
                    line = file_to_parse.readline()
                    if not line:
                        break
                    match = self.pattern.search(line)
                    if self.parser_config.exclude_pattern:
                        match_to_exclude = self.exclusion_pattern.search(line)
                    else:
                        match_to_exclude = None
                    if match is not None and match_to_exclude is None:
                        index = file_to_parse.tell() - len(line)
                        file_matches[index] = {'line_number': line_offset, 'line': line.strip()}
                    line_offset += 1
            if file_matches != {}:
                self.records[file_path].update(file_matches)
            return file_matches
        except Exception as e:
            self.logger.error('Failed to parse file: {}'.format(file_path))
            raise e

    def _get_valid_filename(self, s):
        # Django method of creating a valid filename from a user input string
        s = str(s).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '_', s)

    def _write_records(self, index_file):
        self.logger.debug('AMSFileParser ({}) is indexing matches to {}'.format(
            self.parser_config.file_parser_name, index_file))
        try:
            with open(index_file, 'w+') as record_file:
                pickle.dump(self.records, record_file)
        except pickle.PickleError as e:
            self.logger.error('Unable to write records to index file: {} unexpected data issue: {}'.format(
                index_file, e))
        except Exception as e:
            self.logger.error('Unknown error ({}) occured while attempting to write records to index file: {}'.format(
                e, index_file))

    def _load_index_file(self):
        self.logger.debug('Loading index file: {}'.format(self.index_file))
        try:
            with open(self.index_file, 'r') as existing_file:
                self.records = pickle.load(existing_file)
        except IOError:
            # This should only occur if the index_file does not currently exist since we've already done the needful
            pass
        except pickle.PickleError:
            # Indicates an invalid index_file
            # TODO: Consider trying to make a copy of it for forensics.
            pass
        except Exception as e:
            self.logger.debug('Unable to load the index_file: {}\nException returned: {}'.format(self.index_file, e))

    def _find_index_file(self, path, file_name):
        # Check path, cwd, tmp for current index file
        locations = [path, os.getcwd(), '/tmp']
        index_name = '.{}_{}.index'.format(self._get_valid_filename(self.ams_config_dir), file_name)
        index_file = None
        for location in locations:
            tmp_path = os.path.join(location, index_name)
            if os.path.isfile(tmp_path):
                if os.access(tmp_path, os.R_OK) and os.access(tmp_path, os.W_OK):
                    index_file = tmp_path
                    break
            elif os.access(location, os.W_OK) and os.access(location, os.X_OK):
                index_file = tmp_path
                break
        if index_file is not None:
            self.logger.debug('AMSFileParser ({}) is using index file: {}'.format(self.parser_config.file_parser_name, index_file))
            return index_file
        else:
            self.logger.error('We were not able to find a suitable location to place an index file for {} in the '
                              'following locations [{}]'.format(self.parser_config.file_parser_name, locations))

    def _check_file_age(self, file_name):
        file_stat = os.stat(file_name)
        if file_name and S_ISREG(file_stat.st_mode):
            mtime = file_stat[ST_MTIME]
            file_age_in_days = int((self.current_time - mtime) / SECPERDAY)
            if self.parser_config.max_age == -1 or file_age_in_days <= self.parser_config.max_age:
                return True
            else:
                return False
        else:
            self.logger.debug('The file name {} passed to _check_file_age() is invalid or the file no longer exists.'.format(file_name))
            return False

    @staticmethod
    def walk(top, depth=0, onerror=None, followlinks=False):
        dirs = []
        nondirs = []

        # This is blantant grab of code for scandir.walk() which I have stripped and added depth as an arg.
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
            new_path = os.path.join(top, name)
            if followlinks or not os.path.islink(new_path):
                for entry in AMSFileParser.walk(new_path, depth+1, onerror, followlinks):
                    yield entry
