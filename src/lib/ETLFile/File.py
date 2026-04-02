#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path, json, sys, locale, re, os, ConfigParser, collections, socket

# import codecs, traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Exceptions import *
from lib.Validators import *
from lib.Helpers import *

# noinspection PyUnresolvedReferences
from lib.Custom import *
# noinspection PyUnresolvedReferences
from lib.Custom.DuplicateRemoval import *
# noinspection PyUnresolvedReferences
from overrides.Classes import *

class File(object):
    """This is the master container object for ETL file validation.  All functionality should flow through
    this class in order to standardize validation for ETL processes.

    Attributes:
        col_validators: the validators for each column stored in an array
        errors: an array of errors
        file_path: string of the file path
        json_descriptor_path: string of the json_descriptor_path
        json_schema: parsed json object from the json_descriptor_path
        sample_file: (optional) true|false, denotes whether or not to sample data for the file or read whole file if false
        sample_row_count: (optional) number of rows to sample if "sample" is true, ignored if false
        num_cols_in_file: denotes the number of columns in the file
        header_col: true|false.  if true, col headers are included in file, otherwise there are no header row,
        min_row_count: (optional) but if defined, the file must have this number of rows otherwise alert.
        max_row_count: (optional) but if defined, the file must not have more than this number of rows otherwise alert.
        allow_empty: (optional) true|false, if not defined assumed false
        expected_encoding: expected encoding of ETL file
        fromEncodingIfAutomaticUnknown: If the automatic encoding from resolves to unknown, use this encoding instead of default
        fromEncodingIfFailure: Array of encodings to try if automatic encoding fails with an error
        delimiter: expected column delimiter
        file_size: file size in bytes
        locale: the locale to be used for date validations.  Can be expanded to do currencies etc etc.
        decrypt_script_path: The path to the decrypt script to execute.
        file_validated: This is the bool value that is set after the file is validated successfully
        strip_cols: This is the bool value that will determine if columns should be stripped for whitespace or not.
        min_file_size: This is the minimum file size.
        max_file_size: This is the maximum file size.
        duplicate_check_ary: An array of columns that when concatenated create a unique index or value.
        duplicates_found: A dictionary of duplicates found
        config: configuration file props
        validation_override: holds the override info for writing a custom file validator
        dynamic_vars: holds dynamic variables set and used with custom validators.
        _cached_validators: holds a cached validator object
        hostname: hostname of host running code
    """

    def __init__(self, file_path, json_descriptor_path, debug=False):
        """ This method will auto-invoke the ETL file data integrity process on the *file_path* which is described by the *json_descriptor_path*
        :param file_path: string
        :param json_descriptor_path: string
        :param debug: bool
        :return: File
        """

        # define some defaults
        self.errors = []  # creates a list of errors.
        self.warnings = []  # creates a list of warnings.
        self.col_validators = dict()  # creates a dictionary for validators.
        self.header_col = False  # sets default of header col to False
        self.min_row_count = -1  # sets default of min row count to -1 i.e. not set.
        self.max_row_count = -1  # sets default of max row count to -1 i.e. not set.
        self.allow_empty = False  # sets default of allow empty to False
        self.expected_encoding = 'UTF-8'  # sets default encoding expected to UTF-8
        self.fromEncodingIfAutomaticUnknown = ''  # sets the encoding from to use if it is detected as unknown
        self.fromEncodingIfFailure = []  # list of encodings to try in order if automatic encoding failes.
        self.locale = 'en_US'  # sets default locale to en-US
        self.decrypt_script_path = ''  # sets the default location of the decrypt script path
        self.debug = False  # defaults debug to False.  DO NOT SET THIS DIRECTLY!!! PASS IT IN
        self.file_validated = False  # only set this to true once the file is successfully validated.
        self.strip_cols = False
        self.min_file_size = None
        self.max_file_size = None
        self.duplicate_check_ary = []  # creates a list of duplicate checks
        self.unique_rows_for_dup_checks = dict()  # this is used for dup checks
        self.dup_check_col_validators = dict()  # creates a dictionary for dup check validators
        self.duplicates_found = {}  # keeps track of the duplicates found in any duplicate checks
        self.sample_row_count = 0  # default sample row count to 0
        self.sample_file = False  # default sample file to False
        self.validation_override = None  # this is to override the validate_file method
        self.pre_validation_routines = []  # routines to run prior to validating the content of this file.  File based checks will still occur prior to this
        self.post_validation_routines = []  # routines to run after validating the content of this file.
        self._cached_validators = {}  # holds cached validator objects
        self.dynamic_vars = {}  # holds dynamic variables set and used with custom validators.
        self.shred_file = False  # whether or not to shred the file after decryption when we are done working with it.
        self.hostname = str(socket.gethostname()).strip()
        if self.hostname == 'sasdev1-centos6':
            self.decrypt_script_path = '/home/devshare/python/SAS/general_op_scripts/bash_scripts/utilities/decrypt.sh'
        # set some defaults / setup some config data
        self.config = ConfigParser.ConfigParser()

        abs_file_dir = os.path.abspath(os.path.dirname(__file__))
        self.config.read(os.path.abspath(abs_file_dir + '../../../Config/ssod_validator.cfg'))
        if debug:
            self.debug = True

        # check to see if the file path for the ETL file to parse is a real file
        file_validator = FileExistsValidator(True)
        if not (file_validator.validate(file_path)):
            raise StopBatchTriggerZabbixBatchDelayException('File does not exist: ' + file_path)

        self.file_path = file_path
        self.orig_file_path = file_path

        # check to see if the file path for the JSON descriptor file is a real file
        if not (file_validator.validate(json_descriptor_path)):
            raise StopBatchTriggerZabbixBatchDelayException('JSON descriptor file does not exist: ' + json_descriptor_path)

        self.json_descriptor_path = json_descriptor_path

        # now decode JSON into class object.
        try:
            with open(json_descriptor_path) as json_data:
                self.json_schema = json.load(json_data)

                # check to make sure the 'file' attribute exists.  if it does not, stop the batch
                if 'file' not in self.json_schema:
                    raise StopBatchTriggerZabbixBatchDelayException('JSON descriptor file does not have a valid \'file\' attribute.')

                # now check to see if the data file (file_path) is encrypted.  If it is, attempt to decrypt it
                if file_path.find('.pgp') != -1 or file_path.find('.asc') != -1:
                    self.shred_file = True
                    if 'decryptScriptPath' not in self.json_schema['file']:
                        raise DecryptPgPException('Cannot decrypt input file: ' + self.file_path + ' as no "decryptScriptPath" attribute has been defined in the descriptor file')
                    elif not (file_validator.validate(self.json_schema['file']['decryptScriptPath'])) and self.decrypt_script_path == '':
                        raise DecryptPgPException('Cannot decrypt input file: ' + self.file_path + ' as the "decryptScriptPath" file does not exist or has improper permissions: ' + self.json_schema['file']['decryptScriptPath'])
                    else:
                        if self.debug:
                            print "[NOTE] This file is encrypted, we're going to attempt to automatically decrypt it so we can proceed: " + self.file_path
                        self.orig_file_path = self.file_path
                        decrypt_pgp = DecryptPgP(self.file_path, self.json_schema['file']['decryptScriptPath'])
                        self.file_path = decrypt_pgp.decrypted_file_path

                # get the size in bytes of the file
                self.file_size = os.path.getsize(self.file_path)

                # check if we are going to sample the file or process the whole file.
                self.sample_file = self.json_schema['file']['sample']
                bool_validator = BoolValidator()
                if not (bool_validator.validate(self.sample_file)):
                    raise StopBatchTriggerZabbixBatchDelayException('Invalid \'sample\' parameter: ' + bool_validator.format_errors())
                elif self.sample_file:
                    self.sample_row_count = self.json_schema['file']['sampleRowCount']
                    int_validator = IntValidator()
                    if not (int_validator.validate(self.sample_row_count, {
                        'min': 1
                    })):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'sampleRowCount\' parameter: ' + int_validator.format_errors())

                # check that the number of columns that are supposed to be in the file is set.
                self.num_cols_in_file = self.json_schema['file']['numColsInFile']
                int_validator = IntValidator()
                if not (int_validator.validate(self.num_cols_in_file, {
                    'min': 1
                })):
                    raise StopBatchTriggerZabbixBatchDelayException('Invalid \'num_cols_in_file\' parameter: ' + int_validator.format_errors())

                # check and set if there is a header column in the file
                if 'headerCol' in self.json_schema['file']:
                    self.header_col = self.json_schema['file']['headerCol']
                    bool_validator = BoolValidator()
                    if not (bool_validator.validate(self.header_col)):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'header_col\' parameter: ' + bool_validator.format_errors())

                # check and set if there is a min row count (optional)
                if 'minRowCount' in self.json_schema['file']:
                    self.min_row_count = self.json_schema['file']['minRowCount']
                    int_validator = IntValidator()
                    if not (int_validator.validate(self.min_row_count, {
                        'min': 0
                    })):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'min_row_count\' parameter: ' + int_validator.format_errors())

                # check and set if there is a max row count (optional)
                if 'maxRowCount' in self.json_schema['file']:
                    self.max_row_count = self.json_schema['file']['maxRowCount']
                    int_validator = IntValidator()
                    if not (int_validator.validate(self.max_row_count, {
                        'min': 0
                    })):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'max_row_count\' parameter: ' + int_validator.format_errors())

                # noinspection PyChainedComparisons
                if self.max_row_count > -1 and self.min_row_count > -1 and self.min_row_count > self.max_row_count:
                    raise StopBatchTriggerZabbixBatchDelayException('Max row count (' + str(self.max_row_count) + ') cannot be less than min row count (' + str(self.min_row_count) + ')')

                # check and set if we are allowing the file to be empty or not (optional).  Default false.
                if 'allowEmpty' in self.json_schema['file']:
                    self.allow_empty = self.json_schema['file']['allowEmpty']
                    bool_validator = BoolValidator(True)
                    if not (bool_validator.validate(self.allow_empty)):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'allow_empty\' parameter: ' + bool_validator.format_errors())

                # convert the file using iconv to the charset specified or the default of 'UTF-8' (optional).
                if 'expectedEncoding' in self.json_schema['file']:
                    self.expected_encoding = self.json_schema['file']['expectedEncoding']
                    charset_validator = CharsetValidator()
                    if not (charset_validator.validate(self.expected_encoding)):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'expected_encoding\' parameter: ' + charset_validator.format_errors())

                # encoding to use if automatic encoding check returns unknown (optional)
                if 'fromEncodingIfAutomaticUnknown' in self.json_schema['file']:
                    self.fromEncodingIfAutomaticUnknown = self.json_schema['file']['fromEncodingIfAutomaticUnknown']
                    charset_validator = CharsetValidator()
                    if not (charset_validator.validate(self.fromEncodingIfAutomaticUnknown)):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'fromEncodingIfAutomaticUnknown\' parameter: ' + charset_validator.format_errors())

                # encoding to use if automatic encoding check returns unknown (optional)
                if 'fromEncodingIfFailure' in self.json_schema['file']:
                    self.fromEncodingIfFailure = self.json_schema['file']['fromEncodingIfFailure']
                    charset_validator = CharsetValidator()
                    for tmp_encoding in self.fromEncodingIfFailure:
                        if not (charset_validator.validate(tmp_encoding)):
                            raise StopBatchTriggerZabbixBatchDelayException('Invalid encoding in \'fromEncodingIfFailure\' parameter: ' + charset_validator.format_errors())

                # set and validate delimiter
                if 'delimiter' not in self.json_schema['file']:
                    raise StopBatchTriggerZabbixBatchDelayException('Invalid \'delimiter\' parameter: column delimiter required.')
                self.delimiter = self.json_schema['file']['delimiter']

                # validate proper locale locale specified or the default of 'en_US' (optional).
                if 'locale' in self.json_schema['file']:
                    self.locale = str(self.json_schema['file']['locale']).strip()
                    locale_validator = LocaleValidator()
                    if not (locale_validator.validate(self.locale)):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'locale\' parameter: ' + locale_validator.format_errors())

                # sets the locale
                locale.setlocale(locale.LC_ALL, self.locale)

                # set and validate the stripColsWhitespace
                # check and set if we are allowing the file to be empty or not (optional).  Default false.
                if 'strip_col_whitespace' in self.json_schema['file']:
                    self.strip_cols = self.json_schema['file']['strip_col_whitespace']
                    bool_validator = BoolValidator()
                    if not (bool_validator.validate(self.strip_cols)):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'strip_col_whitespace\' parameter: ' + bool_validator.format_errors())

                # set and validate the min_file_size param
                if 'min_file_size' in self.json_schema['file']:
                    self.min_file_size = self.json_schema['file']['min_file_size']
                    float_validator = FloatValidator()
                    if not (float_validator.validate(self.min_file_size)):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'min_file_size\' parameter: ' + float_validator.format_errors())
                    elif self.min_file_size < 0:
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'min_file_size\' parameter: min file size cannot be less than zero: ' + str(self.min_file_size))

                # set and validate the max_file_size param
                if 'max_file_size' in self.json_schema['file']:
                    self.min_file_size = self.json_schema['file']['max_file_size']
                    float_validator = FloatValidator()
                    if not (float_validator.validate(self.max_file_size)):
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'max_file_size\' parameter: ' + float_validator.format_errors())
                    elif self.min_file_size < 0:
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'max_file_size\' parameter: max file size cannot be less than zero: ' + str(self.max_file_size))
                    elif self.max_file_size < self.min_file_size:
                        raise StopBatchTriggerZabbixBatchDelayException('Invalid \'max_file_size\' parameter: max file size cannot be less than min file size: ' + str(self.max_file_size) + ' < ' + str(self.min_file_size))

                # set and validate the max_file_size param
                if 'duplicateChecks' in self.json_schema['file']:
                    dup_loop_num = 0

                    for dupe_list_str in self.json_schema['file']['duplicateChecks']:
                        self.duplicates_found[dup_loop_num] = {}
                        dup_check_dict = dict()
                        dup_check_dict['removeDuplicates'] = None
                        if type(dupe_list_str) is dict:
                            dup_check_dict['dupe_list'] = []
                            dup_check_dict['dupe_cols_error_txt'] = ''
                            for col_num, validators in dupe_list_str.iteritems():
                                if col_num == 'removeDuplicates':
                                    try:
                                        dup_check_dict['removeDuplicates'] = globals()[validators]()
                                    except Exception as e:
                                        raise StopBatchTriggerZabbixBatchDelayException(validators + ': ' + str(e))
                                else:
                                    self._init_dup_check_validators(col_num, validators)
                                    dup_check_dict['dupe_list'].append(col_num)
                                    dup_check_dict['dupe_cols_error_txt'] += '' if not dup_check_dict['dupe_cols_error_txt'] else ','
                                    dup_check_dict['dupe_cols_error_txt'] += col_num
                        else:
                            dup_check_dict['dupe_cols_error_txt'] = str(dupe_list_str).strip()
                            dup_check_dict['dupe_list'] = dup_check_dict['dupe_cols_error_txt'].split(',')

                        try:
                            dup_check_dict['separator'] = str(self.json_schema['file']['duplicateChecksSeparators'][dup_loop_num]).strip()
                        except IndexError:
                            dup_check_dict['separator'] = ''
                        self.duplicate_check_ary.append(dup_check_dict)
                        self.unique_rows_for_dup_checks[dup_loop_num] = dict()
                        dup_loop_num += 1

                # check to see if there are any pre_validation_routines
                if 'pre_validation_routines' in self.json_schema['file']:
                    if len(self.json_schema['file']['pre_validation_routines']) > 0:
                        for pre_validation_routine in self.json_schema['file']['pre_validation_routines']:
                            new_pre_validation_routine = pre_validation_routine
                            if 'class' not in new_pre_validation_routine:
                                raise Exception('class attribute not found in pre_validation_routines json document')
                            if 'init' not in new_pre_validation_routine:
                                raise Exception('class attribute not found in pre_validation_routines json document')

                            if 'returnVars' not in new_pre_validation_routine:
                                new_pre_validation_routine['returnVars'] = {}

                            new_pre_validation_routine['args'] = self._get_args_for_custom_class(new_pre_validation_routine)
                            self.pre_validation_routines.append(new_pre_validation_routine)

                # check to see if there are any post_validation_routines
                if 'post_validation_routines' in self.json_schema['file']:
                    if len(self.json_schema['file']['post_validation_routines']) > 0:
                        for post_validation_routine in self.json_schema['file']['post_validation_routines']:
                            new_post_validation_routine = post_validation_routine
                            if 'class' not in new_post_validation_routine:
                                raise Exception('class attribute not found in post_validation_routine json document')
                            if 'init' not in new_post_validation_routine:
                                raise Exception('class attribute not found in post_validation_routine json document')

                            if 'returnVars' not in new_post_validation_routine:
                                new_post_validation_routine['returnVars'] = {}

                            new_post_validation_routine['args'] = self._get_args_for_custom_class(post_validation_routine)
                            self.post_validation_routines.append(new_post_validation_routine)

                # check and see if there is a _validate_files() override
                if 'validation_override' in self.json_schema['file']:
                    self.validation_override = self.json_schema['file']['validation_override']
                    if 'class' not in self.validation_override:
                        raise Exception('class attribute not found in validation_override json document')
                    if 'init' not in self.validation_override:
                        raise Exception('class attribute not found in validation_override json document')

                    args_list = self._get_args_for_custom_class(self.validation_override)

                    try:
                        validation_override_to_check = globals()[self.validation_override['class']](*args_list)
                        # noinspection PyUnusedLocal
                        result = getattr(validation_override_to_check, self.validation_override['init'])()
                    except SuccessfulStopValidationException:
                        # catch this exception and rethrow to bubble up to top
                        self.file_validated = True
                        raise
                    except Exception as e:
                        raise StopBatchTriggerZabbixBatchDelayException('Caught Error running custom validation ' + self.validation_override['class'] + ': ' + str(e))

                else:
                    # now let's init the validators on a per column basis and validate that they are indeed properly written in the JSON descriptor file.
                    self._init_col_validators()

                    # now we're going to actually validate the file.  Error messages at this point will be queued up instead of thrown on error.
                    self._validate_file()

        except SuccessfulStopValidationException as e:
            # catch this exception and rethrow to bubble up to top
            self.file_validated = True
            if self.is_data_warning():
                raise WarningValidationException(str(e))
            raise
        except (SkipValidationException, DuplicateRemovalSuccessException):
            self.file_validated = True
            raise
        except Exception as e:
            # traceback.print_exc()
            raise StopBatchTriggerZabbixBatchDelayException('File DQ Exception: ' + str(e))

    # noinspection PyMethodMayBeStatic
    def _get_args_for_custom_class(self, custom_class):
        """
        This method will return an array of arguments to pass into the custom class if they exist.
        Args:
            custom_class: Dynamically passed user defined class.
        Returns: list

        """
        args_list = []
        args_kvp = collections.OrderedDict()
        bool_validator = BoolValidator(True)
        if 'args' in custom_class and len(custom_class['args']) > 0:
            for arg in custom_class['args']:
                for key, value in arg.iteritems():
                    if value and bool_validator.validate(value):
                        args_list.append(eval(key))
                    else:
                        args_list.append(value)

        if len(args_kvp) > 0:
            args_list.append(args_kvp)

        # print '[json dump args] ' + json.dumps(args_list, indent=4)
        # exit()
        return args_list

    def _init_dup_check_validators(self, col_num, col_validator_schema):
        if not col_validator_schema or 'validators' not in col_validator_schema or len(col_validator_schema['validators']) == 0:
            # this allows us to make the column not required.
            self.dup_check_col_validators[int(col_num)] = []
            self.dup_check_col_validators[int(col_num)].append({
                'validator': '', 'options': '', 'required': False, 'label': ''
            })
        else:
            for validator in col_validator_schema['validators']:
                if col_num not in self.dup_check_col_validators:
                    self.dup_check_col_validators[int(col_num)] = []

                self.dup_check_col_validators[int(col_num)].append(self._get_validator_dict(validator, col_validator_schema, col_num))

    def _init_col_validators(self):
        """This method will loop through the JSON file and init the validators for each column.  This should be
        an internal call only"""

        # if there are no columns defined in the json schema: throw an error.
        if 'cols' not in self.json_schema or len(self.json_schema['cols']) == 0:
            raise StopBatchTriggerZabbixBatchDelayException('No validators found for any columns.  \'cols\' node is required.')

        # loop through the columns and save the validators on a per column basis
        for col_num, col_validator_schema in sorted(self.json_schema['cols'].iteritems()):
            try:
                col_num = int(col_num)
            except Exception as e:
                raise StopBatchTriggerZabbixBatchDelayException('Column must be an integer: ' + str(col_num) + ' was passed and is an invalid column number.  Additional info: ' + str(e))
            if 'validators' not in col_validator_schema or len(col_validator_schema['validators']) == 0:
                if 'required' in col_validator_schema and not col_validator_schema['required']:
                    # this allows us to make the column not required.
                    self.col_validators[int(col_num)] = []
                    self.col_validators[int(col_num)].append({
                        'validator': '', 'options': '', 'required': False, 'label': '', 'priority': None
                    })
                    continue
                else:
                    raise StopBatchTriggerZabbixBatchDelayException('No validators found for column number ' + str(col_num) + '.  Validators are required if listed in the file')

            for validator in col_validator_schema['validators']:
                if col_num not in self.col_validators:
                    self.col_validators[int(col_num)] = []

                self.col_validators[int(col_num)].append(self._get_validator_dict(validator, col_validator_schema, col_num))

        # print self.col_validators
        return True

    # noinspection PyMethodMayBeStatic
    def _get_validator_dict(self, validator, col_validator_schema, col_num):
        """
        This builds a validator dictionary
        :param validator: dict
        :param col_validator_schema: dict
        :param col_num: int
        :return: dict
        """
        if 'validator' not in validator or validator['validator'] is None or not validator['validator']:
            raise StopBatchTriggerZabbixBatchDelayException('Empty validator defined for column number ' + str(col_num) + '.  Validators are required if defined.')

        # set some defaults for the column
        validator_options = None
        col_required = True
        label = None
        priority = 'error'

        # check if this is a valid validator
        try:
            # validator_to_call().validate()
            validator_to_check = globals()[validator['validator'] + 'Validator']()
            getattr(validator_to_check, 'validate')
            validator_to_call = validator['validator'] + 'Validator'
        except Exception as e:
            raise StopBatchTriggerZabbixBatchDelayException('Validator: ' + str(validator['validator']) + 'Validator' + ' does not exist or is not implemented for column ' + str(col_num) + '.  Exception: ' + str(e))

        if 'options' in validator and validator['options'] is not None and validator['validator']:
            validator_options = validator['options']

        if 'required' in col_validator_schema and not col_validator_schema['required']:
            col_required = False

        if 'label' in col_validator_schema and col_validator_schema['label']:
            label = col_validator_schema['label'].strip()

        if 'priority' in col_validator_schema and col_validator_schema['priority']:
            priority = col_validator_schema['priority'].strip()

        # print 'validator for col[' + str(col_num) + ']: '
        # print 'options: ' + str(validator_options)
        # print 'validator: ' + str(validator_to_call)
        # print 'required: ' + str(col_required)
        # print 'priority:' + str(priority)

        return {
            'validator': validator_to_call, 'options': validator_options, 'required': col_required, 'label': label, 'priority': priority
        }

    # noinspection PyTypeChecker
    def _validate_file(self):
        """This method will kick off the validation of the data within the file.  This should be an internal call only"""
        filename_to_dq = self.file_path

        # doing pre_validation_routines
        if len(self.pre_validation_routines) > 0:
            for pre_validation_routine in self.pre_validation_routines:
                try:
                    pre_validation_routine_to_check = globals()[pre_validation_routine['class']](*pre_validation_routine['args'])
                    # noinspection PyUnusedLocal
                    pre_validation_routine_to_check_result = getattr(pre_validation_routine_to_check, pre_validation_routine['init'])()
                    if len(pre_validation_routine['returnVars']) > 0:
                        for k, v in pre_validation_routine['returnVars'].iteritems():
                            constructed_statement = k + "=" + v
                            # print 'constructed_statement: ' + constructed_statement
                            exec constructed_statement

                except (SkipValidationException, DuplicateRemovalSuccessException):
                    raise
                except FileValidateTransDateException as e:
                    raise StopBatchTriggerZabbixBatchDelayException(str(e))
                except Exception as e:
                    raise StopBatchTriggerZabbixBatchDelayException(pre_validation_routine['class'] + ': ' + str(e))

        if self.file_size < 1 and not self.allow_empty:
            raise StopBatchTriggerZabbixBatchDelayException('File ' + self.file_path + ' is empty and it is not allowed to be!')
        elif self.file_size < 1:
            raise SuccessfulStopValidationException('File is empty and is allowed to be empty - success')
        elif self.min_file_size is not None and self.file_size < self.min_file_size:
            raise StopBatchTriggerZabbixBatchDelayException('File is too small: ' + str(self.file_size) + ' < ' + str(self.min_file_size))
        elif self.max_file_size is not None and self.file_size > self.max_file_size:
            raise StopBatchTriggerZabbixBatchDelayException('File is too big: ' + str(self.file_size) + ' > ' + str(self.max_file_size))

        # handling encoding the file
        if self.expected_encoding:
            encoder = EncodingHelper(self.file_path)
            encoder.convert_file_encoding(self.expected_encoding, from_encoding_if_automatic_unknown=self.fromEncodingIfAutomaticUnknown, from_encoding_if_error=self.fromEncodingIfFailure)
            filename_to_dq = encoder.get_encoded_filename()

        with open(filename_to_dq) as fp:
            row_count = 1
            try:
                for row in fp:
                    # support for different charsets:
                    row = unicode(row, self.expected_encoding)
                    # row = unicode(row.strip(codecs.BOM_UTF8), self.expected_encoding)
                    # if self.expected_encoding == 'UTF-8':
                    #     row = unicode(row.strip(codecs.BOM_UTF8), self.expected_encoding)
                    # else:
                    #     row = unicode(row, self.expected_encoding)

                    # if the strip_cols attribute was set for this file, strip it
                    row_stripped = False
                    if self.strip_cols:
                        row = row.strip()
                        row_stripped = True

                    if (not row_stripped and row.strip() == "") or (row_stripped and row == ""):
                        # print '.....SKIPPING EMPTY ROW # ' + str(row_count) + '...'
                        self.add_error('[ROW ' + str(row_count) + '] Empty Row!')
                        row_count += 1
                        continue
                    # if there is a header col, let's skip it
                    if self.header_col and row_count == 1:
                        row_count += 1
                        continue

                    if self.delimiter == '\\t':
                        cols = re.split(r'\t', row)
                    else:
                        cols = row.split(self.delimiter)
                    col_counter = 0
                    col_len = len(cols)
                    if int(col_len) != int(self.num_cols_in_file):
                        self.add_error('[ROW ' + str(row_count) + ']  has ' + str(col_len) + ' columns while descriptor file is expecting ' + str(self.num_cols_in_file) + '.  Start counting columns from #1 (not zero).')
                        row_count += 1
                        continue

                    # used for dup check code
                    clean_cols = []
                    cached_presence_of_validator = PresenceOfValidator(self.debug)
                    for col in cols:
                        # if the strip_cols attribute was set for this file, strip it
                        if self.strip_cols:
                            col = col.strip()
                        # handling different charsets:
                        col = col.encode(self.expected_encoding)
                        # for the very last column in the file, we need to remove any EOL chars.  The following should handle
                        # MAC, Windows and Linux

                        # if self.expected_encoding == 'UTF-8':
                        #     col = unicode(col.strip(codecs.BOM_UTF8), self.expected_encoding)
                        # else:
                        #     col = unicode(col, self.expected_encoding)

                        col = unicode(col, self.expected_encoding)
                        if col_counter == (int(self.num_cols_in_file) - 1):
                            col_input = col.rstrip('\r\n')
                        else:
                            col_input = col
                        # col_input = col.strip()
                        clean_cols.append(col_input)
                        if col_counter in self.col_validators:
                            # Set some column specific vars to let us do 'or' validators.  i.e. Int or InclusionIn.
                            col_failed = False
                            tmp_col_errors = []
                            # Loop through the validators for the column and check if required.
                            validator_cnt = 0
                            for validator in self.col_validators[col_counter]:
                                # if cached validators
                                if not col_counter in self._cached_validators:
                                    self._cached_validators[col_counter] = {}

                                if not validator_cnt in self._cached_validators[col_counter]:
                                    self._cached_validators[col_counter][validator_cnt] = {}

                                if self._cached_validators[col_counter][validator_cnt]:
                                    validator_to_run = self._cached_validators[col_counter][validator_cnt]['validator']
                                    col_label = self._cached_validators[col_counter][validator_cnt]['col_label']
                                    priority = self._cached_validators[col_counter][validator_cnt]['priority']
                                else:
                                    if not validator["validator"]:
                                        col_label = ''
                                        validator_to_run = None
                                        priority = 'error'
                                    else:
                                        validator_to_run = globals()[validator["validator"]](self.debug)
                                        col_label = validator['label'] if validator['label'] else str(validator_to_run)
                                        priority = validator['priority']

                                    self._cached_validators[col_counter][validator_cnt]['validator'] = validator_to_run
                                    self._cached_validators[col_counter][validator_cnt]['col_label'] = col_label
                                    self._cached_validators[col_counter][validator_cnt]['priority'] = priority

                                try:
                                    priority_method = getattr(self, 'add_' + priority)
                                except Exception as e:
                                    raise StopBatchTriggerZabbixBatchDelayException('Invalid priority specified ' + priority + ' - ' + str(e))

                                # reset the cached validator errors:
                                if validator_to_run is not None:
                                    validator_to_run.reset_errors()
                                # presence_of_validator = PresenceOfValidator(self.debug)
                                cached_presence_of_validator.reset_errors()
                                is_field_populated = cached_presence_of_validator.validate(col_input, col_counter)
                                if not is_field_populated and validator["required"]:
                                    priority_method('[ROW ' + str(row_count) + '][COLUMN ' + str(col_counter) + '][' + col_label + '] is empty in a required column.')
                                    break
                                elif not validator["required"] and not validator["validator"]:
                                    # skipping as the field is not required and there is no validator
                                    continue
                                elif not is_field_populated and not validator["required"]:
                                    # skipping as the field is not populated and it is not required
                                    continue
                                if not validator_to_run.validate(col_input, self._interpret_options(validator["options"])):
                                    col_failed = True
                                    for validator_error in validator_to_run.get_errors():
                                        tmp_col_errors.append('[ROW ' + str(row_count) + '][COLUMN ' + str(col_counter) + '][' + str(col_label) + ']' + str(validator_error))
                                else:
                                    # if even one validator passes, we break out of the validator loop
                                    col_failed = False
                                    break

                                validator_cnt += 1

                            if col_failed:
                                for validator_error_str in tmp_col_errors:
                                    priority_method(validator_error_str)
                        else:
                            # presence_of_validator = PresenceOfValidator(self.debug)
                            cached_presence_of_validator.reset_errors()
                            if not cached_presence_of_validator.validate(col_input, col_counter):
                                for validator_error in cached_presence_of_validator.get_errors():
                                    priority_method('[ROW ' + str(row_count) + '][COLUMN ' + str(col_counter) + '][' + str(cached_presence_of_validator) + ']' + str(validator_error))
                        col_counter += 1

                    # dup check code
                    if len(self.duplicate_check_ary) > 0:
                        dup_check_num = 0
                        for dup_check in self.duplicate_check_ary:
                            unique_value = ''
                            include_value = True
                            for col_num in dup_check['dupe_list']:
                                col_num_int = int(col_num)
                                # this is if we have validators on a per column basis
                                if len(self.dup_check_col_validators) > 0 and len(self.dup_check_col_validators[col_num_int]) > 0:
                                    for validator in self.dup_check_col_validators[col_num_int]:
                                        if not validator["validator"]:
                                            continue
                                        validator_to_run = globals()[validator["validator"]](self.debug)
                                        if not validator_to_run.validate(clean_cols[col_num_int], self._interpret_options(validator["options"])):
                                            include_value = False
                                if not include_value:
                                    break
                                unique_value += dup_check['separator'] if unique_value else ''
                                unique_value += str(clean_cols[col_num_int])
                            if not include_value:
                                continue

                            if not unique_value in self.unique_rows_for_dup_checks[dup_check_num]:
                                self.unique_rows_for_dup_checks[dup_check_num][unique_value] = str(row_count)
                            else:
                                if unique_value not in self.duplicates_found[dup_check_num]:
                                    self.duplicates_found[dup_check_num][unique_value] = {}
                                    self.duplicates_found[dup_check_num][unique_value]['lines'] = []
                                    self.duplicates_found[dup_check_num][unique_value]['lines'].append(self.unique_rows_for_dup_checks[dup_check_num][unique_value])

                                self.duplicates_found[dup_check_num][unique_value]['lines'].append(str(row_count))

                                err_msg = '[ROW ' + str(row_count) + '][DUP CHECK #' + str((dup_check_num + 1)) + '][DUPLICATES ROW ' + self.unique_rows_for_dup_checks[dup_check_num][unique_value] + '][COLS ' + str(dup_check['dupe_cols_error_txt']) + '] are not unique'
                                if self.debug:
                                    err_msg += ': ' + str(unique_value)
                                self.add_error(err_msg)
                            dup_check_num += 1

                    # check to make sure that the number of columns that are in the 1st row match what is defined in the descriptor file (only done
                    # on first row)
                    if int(col_counter) != int(self.num_cols_in_file) and row_count <= 1:
                        raise StopBatchTriggerZabbixBatchDelayException('[ROW ' + str(row_count) + '] ' + self.file_path + ' has ' + str(col_counter) + ' columns while descriptor file is expecting ' + str(self.num_cols_in_file) + '.  Start counting columns from #1 (not zero).')

                    if self.sample_file and self.sample_row_count <= row_count:
                        # print warnings (if any)
                        self._print_warnings()
                        if self.is_data_error():
                            print self.format_errors()
                            raise StopBatchTriggerZabbixBatchDelayException('There have been ' + str(len(self.errors)) + ' errors ')
                        else:

                            self.file_validated = True
                            raise SuccessfulStopValidationException('No validation errors have been found during a sample of ' + str(row_count) + ' rows')
                    row_count += 1

                # duplicate removal code:
                # noinspection PyUnusedLocal
                try:
                    if len(self.duplicate_check_ary) > 0:
                        dup_check_num = 0
                        for dup_check in self.duplicate_check_ary:
                            if dup_check['removeDuplicates']:
                                dup_check['removeDuplicates'].remove_duplicates(filename_to_dq, self.duplicates_found[dup_check_num])
                            dup_check_num += 1
                except DuplicateRemovalSuccessException:
                    raise
                except Exception as e:
                    print self.format_errors()
                    raise

            finally:
                # doing post_validation_routines
                if len(self.post_validation_routines) > 0:
                    for post_validation_routine in self.post_validation_routines:
                        try:
                            post_validation_routine_to_check = globals()[post_validation_routine['class']](*post_validation_routine['args'])
                            # noinspection PyUnusedLocal
                            post_validation_routine_to_check_result = getattr(post_validation_routine_to_check, post_validation_routine['init'])()
                            if len(post_validation_routine['returnVars']) > 0:
                                for k, v in post_validation_routine['returnVars'].iteritems():
                                    constructed_statement = k + "=" + v
                                    # print 'constructed_statement: ' + constructed_statement
                                    exec constructed_statement

                        except (SkipValidationException, DuplicateRemovalSuccessException):
                            raise
                        except Exception as e:
                            raise StopBatchTriggerZabbixBatchDelayException('Caught Error running post_validation_routine ' + post_validation_routine['class'] + ': ' + str(e))
                # truncate the iconv converted file on any exception and rethrow the exception
                if self.shred_file:
                    FileShredder(filename_to_dq)

        # Fixing row count (hack) since we're incrementing row count at the bottom of every row and starting w/ 1
        row_count -= 1

        # print warnings (if any)
        self._print_warnings()
        if self.is_data_error():
            self._check_min_max_row_count(row_count)
            print self.format_errors()
            raise StopBatchTriggerZabbixBatchDelayException('There have been ' + str(len(self.errors)) + ' errors ')
        else:
            # check the min / max row counts in the file.
            self._check_min_max_row_count(row_count, "exception")
            self.file_validated = True
            raise SuccessfulStopValidationException('No validation errors have been found!')

    def _print_warnings(self):
        """
        This method will print warnings in a standardized way.
        """
        if self.is_data_warning():
            print '********************* START WARNINGS *********************'
            print self.format_warnings()
            print '********************* END WARNINGS ***********************'

    def _interpret_options(self, options):
        # noinspection PyTypeChecker
        if isinstance(options, dict):
            for k, v in options.iteritems():
                v = str(v)
                if v.find('dynamic_vars|') > -1:
                    v_split = v.split('|')
                    if len(v_split) > 1 and v_split[1] in self.dynamic_vars:
                        options[k] = self.dynamic_vars[v_split[1]]
        elif isinstance(options, basestring):
            if options.find('dynamic_vars|') > -1:
                v_split = options.split('|')
                if v_split[1] in self.dynamic_vars:
                    options = self.dynamic_vars[v_split[1]]
        elif isinstance(options, list):
            tmp_list = list()
            for v in options:
                v = str(v)
                if v.find('dynamic_vars|') > -1:
                    v_split = v.split('|')
                    if len(v_split) > 1 and v_split[1] in self.dynamic_vars:
                        tmp_list.append(self.dynamic_vars[v_split[1]])
                    else:
                        tmp_list.append(v)
                else:
                    tmp_list.append(v)
            options = tmp_list
        elif options is None:
            pass
        else:
            print '[OPTION NOT DETECTED] _interpret_options' + str(type(options))

        return options

    def _check_min_max_row_count(self, rows_in_file, exception_or_error="error"):
        """ This method will check the row counts in the file to make sure the file meets the row count expectations.
        :param rows_in_file: int
        :return: none
        """
        error_msg = ""
        # noinspection PyChainedComparisons
        if self.min_row_count > rows_in_file and self.min_row_count > -1:
            # if the file doesn't contain the minimum number of expected rows.
            error_msg = '[FILE_ERROR] Expected >= ' + str(self.min_row_count) + ' rows and this file contained: ' + str(rows_in_file)
        elif rows_in_file > self.max_row_count and self.max_row_count > -1:
            # if the file contains more than the maximum number of expected rows.
            error_msg = '[FILE_ERROR] Expected <= ' + str(self.max_row_count) + ' rows and this file contained: ' + str(rows_in_file)

        if error_msg is not "":
            if exception_or_error is "error":
                self.add_error(error_msg)
            else:
                raise StopBatchTriggerZabbixBatchDelayException(error_msg)

    def __str__(self):
        """magic method when you call print(File) to print out a list of the class vars"""
        attributes = vars(self)
        return os.linesep + "------" + os.linesep.join("%s: %s" % item for item in attributes.items())

    def add_error(self, error_message):
        """Adds an error message to the internal errors list in order to keep track of all errors.

        :type error_message: str
        :param error_message: Error message
        """
        self.errors.append(error_message)
        return True

    def add_warning(self, warning_message):
        """Adds a warning message to the internal warning list in order to keep track of all warnings.

                :type warning_message: str
                :param warning_message: Warning message
                """
        self.warnings.append(warning_message)
        return True

    def format_errors(self):
        """ This method will take all errors, if any, and return a formatted string of the errors

        :return: str
        """
        if len(self.errors) == 0:
            return ""
        return OutputFormatHelper.join_output_from_list(self.errors)

    def format_warnings(self):
        """ This method will take all warnings, if any, and return a formatted string of the warnings

        :return: str
        """
        if len(self.warnings) == 0:
            return ""
        ret_str = OutputFormatHelper.join_output_from_list(self.warnings)
        ret_str += os.linesep
        ret_str += '[WARNING] There have been ' + str(len(self.warnings)) + ' warnings'

        return ret_str

    def is_data_error(self):
        """ This method will return bool if there are errors in the data inputs for this file
        :return: bool
        """

        return len(self.errors) > 0

    def is_data_warning(self):
        """ This method will return bool if there are warnings in the data inputs for this file
            :return: bool
        """
        return len(self.warnings) > 0

    def is_file_validated_successfully(self):
        """ This method will let return True if the file has successfully passed validation
        :return: bool
        """
        return self.file_validated