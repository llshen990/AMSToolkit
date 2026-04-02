#!/usr/bin/python

# @author owhoyt
# This file should be added as the crontab entry in order to validate landing files.

# import libraries
import ConfigParser
import json
import os
import shutil
import socket
import sys
import time
import traceback
# traceback
from os import listdir
from os.path import isfile, join

from lib.ETLFile import *
from lib.Exceptions import *
from lib.Helpers import *
from lib.Validators import *

# start the proc check to ensure that this script cannot possibly run more than once at a time
procCheck = ProcCheck(__file__, os.getpid())
procCheck.add_extra_grep('sudo', True)
procCheck.am_i_already_running()

# abs path to file directory:
abs_file_dir = os.path.abspath(os.path.dirname(__file__))

# replace stdout with our custom logger in order to send emails.
complete_validator_output_file = abs_file_dir + '/_complete_validator_output_' + str(int(time.time())) + '.log'
orig_stdout_raw = sys.stdout
sys.stdout = Logger(complete_validator_output_file)
orig_stdout = sys.stdout


def create_validated_file(file_1, file_2):
    Md5Sum().create_validated_md5_file(file_1, file_2)
    if file_exists_validator.validate(file_2):
        if debug:
            print('[POST_ACTIONS] Successfully created validated landing file w/ hash at: ' + file_2)
    else:
        print('[POST_ACTIONS_ERROR] Failed to create validated landing file w/ hash at: ' + file_2)


def update_batch_status_success(validated_file):
    if '_usd_' in validated_file:
        batch_cycle = 'USD_REPORT'
        run_date = RunDate('USDReport', os.path.join('USDReport', 'transaction_dates_processed'), '%Y%m%d')
    else:
        batch_cycle = 'DAILY_CYCLE'
        run_date = RunDate('dailycycle_transaction_date', 'transaction_dates_processed', '%Y%m%d')

    run_date.get_current_run_date()

    file_type = FileGetFileType()
    ft = file_type.get_file_type_from_filename(validated_file)
    file_get_trans_date = FileGetTransDate()
    file_tran_date = file_get_trans_date.get_trans_date_from_filename(validated_file)
    file_tran_date_str = file_tran_date.strftime('%Y%m%d')

    if int(file_tran_date_str) < int(run_date.current_run_date):
        # don't need to update the batch status for files that have already been processed by the system
        return True

    calling_scirpt_type = ft + '_' + file_tran_date_str
    batch_status = UpdateBatchStatus()
    batch_status.update_batch_status(calling_scirpt_type, 'DQ_SUCCESS', validated_file + ' PASSED_DQ', file_tran_date_str, batch_cycle)
    return True


def move_failed_file(failed_file, input_err_string):
    destination_filename = os.path.basename(failed_file)
    file_specific_failed_folder = failed_dq_folder + '/' + os.path.basename(destination_filename)
    if not os.path.exists(file_specific_failed_folder):
        os.makedirs(file_specific_failed_folder)

    fev = FileExistsValidator(True)
    if fev.validate(file_specific_failed_folder + '/' + destination_filename):
        destination_filename += '_' + str(time.time())

    shutil.move(failed_file, file_specific_failed_folder + '/' + destination_filename)

    manifest_file_orig = failed_file.replace('file.', 'manifest.')
    if fev.validate(manifest_file_orig):
        manifest_file_destination = destination_filename.replace('file.', 'manifest.')
        shutil.move(manifest_file_orig, file_specific_failed_folder + '/' + manifest_file_destination)

    if '_usd_' in failed_file:
        batch_cycle = 'USD_REPORT'
        run_date = RunDate('USDReport', os.path.join('USDReport', 'transaction_dates_processed'), '%Y%m%d')
    else:
        batch_cycle = 'DAILY_CYCLE'
        run_date = RunDate('dailycycle_transaction_date', 'transaction_dates_processed', '%Y%m%d')

    run_date.get_current_run_date()

    file_type = FileGetFileType()
    ft = file_type.get_file_type_from_filename(failed_file)
    file_get_trans_date = FileGetTransDate()
    file_tran_date = file_get_trans_date.get_trans_date_from_filename(failed_file)
    file_tran_date_str = file_tran_date.strftime('%Y%m%d')

    if int(file_tran_date_str) < int(run_date.current_run_date):
        # don't need to update the batch status for files that have already been processed by the system
        return True

    calling_scirpt_type = ft + '_' + file_tran_date_str
    batch_status = UpdateBatchStatus()
    batch_status.update_batch_status(calling_scirpt_type, 'DQ_ERROR', failed_file + ':' + os.linesep + input_err_string[0:3000], file_tran_date_str, batch_cycle)
    return True


# set some defaults / setup some config data
config = ConfigParser.ConfigParser()
config.read(abs_file_dir + '/Config/ssod_validator.cfg')
environment = config.get('DEFAULT', 'env')
config_section = config.get('DEFAULT', 'market_config_section')
email = config.get('DEFAULT', 'email')
verbosity = config.get('DEFAULT', 'verbosity')

# failed DQ folder
failed_dq_folder = config.get('DEFAULT', 'failed_dq_folder')
if not failed_dq_folder:
    failed_dq_folder = "/sso/transport/incoming/failed_dq"

# if failed DQ folder does not exist, create it
if not os.path.exists(failed_dq_folder):
    os.makedirs(failed_dq_folder)

if verbosity == 'all':
    verbosity = True
else:
    verbosity = False
debug = config.getboolean('DEFAULT', 'debug')
hostname = str(socket.gethostname()).strip()
if config.has_option('ENV_HOSTNAME_LOOKUP', hostname):
    host_env = config.get('ENV_HOSTNAME_LOOKUP', hostname)
else:
    host_env = 'UNK_ENV'

# Sets DQ Jira integration config
if config.has_option('DEFAULT', 'dq_error_assignee'):
    dq_error_assignee = config.get('DEFAULT', 'dq_error_assignee')
else:
    dq_error_assignee = None

if config.has_option('DEFAULT', 'dq_error_priority'):
    dq_error_priority = config.get('DEFAULT', 'dq_error_priority')
else:
    dq_error_priority = None

if config.has_option('DEFAULT', 'dq_warning_assignee'):
    dq_warning_assignee = config.get('DEFAULT', 'dq_warning_assignee')
else:
    dq_warning_assignee = None

if config.has_option('DEFAULT', 'dq_warning_priority'):
    dq_warning_priority = config.get('DEFAULT', 'dq_warning_priority')
else:
    dq_warning_priority = None

if config.has_option('DEFAULT', 'dq_enable_auto_jira'):
    dq_enable_auto_jira = config.getboolean('DEFAULT', 'dq_enable_auto_jira')
else:
    dq_enable_auto_jira = False
# end DQ Jira config
# sets a global validation error var so we know how to exit the process pending no execution halting exceptions
file_validation_errors = False
# keeps track of the number of files validated.  We don't want to send emails if everything was skipped and nothing
# was validated.
num_files_validated = 0
exit_value = 0

print "**************************************************************"
print "Starting SSOD Data Quality Check"
print "Initiating config from " + environment + ' - ' + config_section
if debug:
    print "[DEBUG] Debug is ON!!!"
print "**************************************************************\n"

try:
    # first we check the landing directory specified by the config.
    landing_dir = str(config.get('DEFAULT', 'landingdir')).strip()

    # if the landing directory doesn't exist, exit w/ exception
    file_exists_validator = FileExistsValidator(True)
    if not os.path.exists(landing_dir):
        raise Exception(landing_dir + " does not exist")

    # get the landing files into a list
    landing_files = [f for f in listdir(landing_dir) if isfile(join(landing_dir, f))]

    # check to see if there are any files in the list, if there are not, exit w/ an exception
    presence_of_validator = PresenceOfValidator(True)
    if not (presence_of_validator.validate(landing_files, 'landing_files', True)):
        raise Exception('No files in landing dir: ' + landing_dir + '. Exiting...')

    # Get the 'validated' landing files directory location from the config
    landing_files_validated_dir = config.get(config_section, 'validated_dir')
    # get the 'validated output' landing files directory location.  This location will house the output of each individual file
    per_file_validation_output_dir = str(config.get(config_section, 'validation_output_dir')).strip()
    # if the landing dir validated files dir does not exist, create it.  Won't exist upon first run as nothing has
    # been validated yet.
    if not os.path.exists(landing_files_validated_dir):
        os.makedirs(landing_files_validated_dir)

    # check to make sure that the individual file output directory is there, if not, create it
    if not os.path.exists(per_file_validation_output_dir):
        os.makedirs(per_file_validation_output_dir)

    # get a list of the files that has been validated already.
    validated_files = [f for f in listdir(landing_files_validated_dir) if isfile(join(landing_files_validated_dir, f))]

    # load the JSON from the config that describes which files this environment will validate and what JSON
    # descriptor files will be used to validate against.
    files_to_validate_json = json.loads(str(config.get(config_section, 'files_to_validate')).replace("'", '"'))

    # if the JSON is empty, exit w/ an exception
    if not (presence_of_validator.validate(files_to_validate_json, 'Files to validate JSON')):
        raise Exception('No JSON in config')

    # now we want to loop through the 'landing files' and try to match up validators against them
    # and actually perform the validations
    inclusion_in_validator = InclusionInValidator(True)
    for landing_file in landing_files:
        # create the validated landing file path so we can see if it exists.
        validate_landing_file = landing_file + config.get(config_section, 'validated_file_postfix')
        validate_landing_file_with_path = str(landing_files_validated_dir + '/' + validate_landing_file).strip()
        per_file_validation_output_file = str(per_file_validation_output_dir + '/' + landing_file).strip()

        # if the landing file has a corresponding 'validated' file, we need to check to see if the md5(landing_file) = contents of the validated file
        # as once we validate a file, we store the md5() of the landing file in the 'validated' folder so we can see if we need to re-validate
        if presence_of_validator.validate(validate_landing_file_with_path, 'validated_files', True) and inclusion_in_validator.validate(validate_landing_file, validated_files):
            # if the md5(landing_file) == the hash stored in the validated file, we know it's already been validated successfully and since
            # the md5() hashes match, we don't need to re-validate as the file hasn't changed since it successfully validated.
            if Md5Sum().compare_hash_for_landing_and_validated_files(str(landing_dir + '/' + landing_file).strip(), validate_landing_file_with_path):
                if debug:
                    print '======================================================================'
                    print "[SKIP] already validated hash check: " + landing_file
                    print '======================================================================'
                continue

        regex_validator = RegExValidator(True)
        # loop through the JSON in the config file.  This will give us the descriptor file (JSON) and the corresponding RegEx's that fall under
        # that descriptor
        for descriptor_file in files_to_validate_json:
            this_file_error = True
            this_file_validation_skipped = False
            # check to make sure the descriptor file is there and readable.  Exit w/ exception if there is an issue.
            descriptor_file_with_path = config.get(config_section, 'json_descriptor_dir') + '/' + descriptor_file
            if not (file_exists_validator.validate(descriptor_file_with_path)):
                raise Exception('Descriptor file: ' + descriptor_file_with_path + ' does not exist')

            # loop through the regex's that fall under the descriptor file.
            for regex in files_to_validate_json[descriptor_file]:
                # if the regex under this descriptor file matches the file, then we need to validate the file
                if regex_validator.validate(landing_file, regex):
                    # this will allow us to log to std out + a separate file for each ETL file so we can go back in and see what the error was w/o logging the entire cron output to a file every time.
                    sys.stdout = Logger(per_file_validation_output_file)

                    # put together the full path of the landing file
                    landing_file_with_path = landing_dir + '/' + landing_file
                    # validate the full path of the landing file just to make sure we didn't screw it up :)
                    if not (file_exists_validator.validate(landing_file_with_path)):
                        raise Exception('Landing file with full path: ' + landing_file_with_path + ' does not exist')

                    # keep track if file has warnings
                    file_warnings = False

                    # ok, this is where the real work goes.  We need to validate the file.  To do this, we need to pass
                    # off the validation to the ssodETLProcess.py
                    etl_file = None
                    try:
                        print '======================================================================'
                        print '[FOUND_FILE] ' + landing_file_with_path
                        etl_file = File(landing_file_with_path, descriptor_file_with_path, debug)
                        # if etl_file.is_file_validated_successfully(): #@todo delete this and uncomment line below.
                        if not (etl_file.is_file_validated_successfully()):
                            file_validation_errors = True
                            print('[FILE_FAILED_VALIDATION] ' + str(len(etl_file.errors)) + ' errors found in ' + landing_file)
                        else:
                            print('[FILE_SUCCESS] File passed validations.')
                    except StopBatchTriggerZabbixBatchDelayException as e:
                        print('[FILE_FAILED_VALIDATION][EXCEPTION] ' + str(e))
                        # traceback.print_exc()
                        # there was an error, let's set the overall validation of this run to a failure
                        file_validation_errors = True
                    except WarningValidationException as e:
                        print('[FILE_SUCCESS_WITH_WARNINGS] ' + str(e))
                        this_file_error = False
                        file_warnings = True
                    except SuccessfulStopValidationException as e:
                        print('[FILE_SUCCESS] ' + str(e))
                        this_file_error = False
                    except SkipValidationException as e:
                        this_file_error = False
                        this_file_validation_skipped = True
                        print('[FILE_SKIPPED] File has been skipped for validation.')
                    except DuplicateRemovalSuccessException as e:
                        print '[DUPLICATES REMOVED] ' + str(e)
                        this_file_error = False
                        this_file_validation_skipped = True
                    except Exception as e:
                        print('[FILE_FAILED_VALIDATION][UNKNOWN_EXCEPTION] ' + str(e))
                        file_validation_errors = True
                    finally:
                        if debug:
                            print('[POST_ACTIONS] Trying to create validated file hash...')

                        if not this_file_validation_skipped:
                            create_validated_file(landing_file_with_path, validate_landing_file_with_path)
                        print '======================================================================'
                        sys.stdout.close_logger()

                        if this_file_error and not debug and dq_enable_auto_jira:
                            dq = DQErrorAutoJiraHelper()
                            dq.assignee = dq_error_assignee
                            dq.priority = dq_error_priority
                            dq_err_string = str(sys.stdout.get_log_file_contents()).strip()
                            # limit the dq_error_string to 10000 chars.
                            dq.set_parameters(landing_file_with_path, dq_err_string[0:10000])
                            dq.send_zabbix_message()
                        elif this_file_error and debug:
                            print '[DEBUG] debug is on and thus cannot fire auto-jira due to PII concerns.'
                        elif file_warnings and debug:
                            print '[DEBUG] debug is on and thus cannot fire aut-jira due to PII concerns.'
                        elif file_warnings and not debug and dq_enable_auto_jira:
                            dq = DQWarningAutoJiraHelper()
                            dq.assignee = dq_warning_assignee
                            dq.priority = dq_warning_priority
                            dq_warning_string = str(sys.stdout.get_log_file_contents()).strip()
                            # limit the dq_error_string to 10000 chars.
                            dq.set_parameters(landing_file_with_path, dq_warning_string[0:10000])
                            dq.send_zabbix_message()

                        if this_file_error:
                            dq_err_string = str(sys.stdout.get_log_file_contents()).strip()
                            move_failed_file(landing_file_with_path, dq_err_string)
                        else:
                            update_batch_status_success(landing_file_with_path)

                        if not this_file_validation_skipped:
                            num_files_validated += 1

                        # rename the file log output to append with a '_success' or '_error' depending on the status
                        if this_file_validation_skipped:
                            shutil.move(per_file_validation_output_file, per_file_validation_output_file + '_skipped')
                        else:
                            shutil.move(per_file_validation_output_file, per_file_validation_output_file + ('_success' if not this_file_error else '_error'))

                        sys.stdout = orig_stdout

except Exception as e:
    sys.stdout = orig_stdout
    print "Caught exception running data quality check:\n"
    print str(e)
    traceback.print_exc()
    file_validation_errors = True
    exit_value = 2
finally:
    sys.stdout = orig_stdout
    print "\n**************************************************************"
    if file_validation_errors:
        print '[GLOBAL][ERROR] One or more files failed to validate successfully.  See output...'
    else:
        print '[GLOBAL][SUCCESS] All files validated successfully'
    print "End SSOD Data Quality Check"
    print "**************************************************************"
    sys.stdout.close_logger()

    try:
        if email and not debug:
            email_validator = EmailValidator(True)
            if email_validator.validate_email_list(email):
                if email_validator.validate_email_list(email) and num_files_validated > 0:
                    sas_email = SASEmail()
                    sas_email.set_from('replies-disabled@sas.com')
                    sas_email.set_to(email)
                    dq_status = ('SUCCESS' if not file_validation_errors else 'ERROR')
                    sas_email.set_subject("[" + config_section + ' ' + host_env + ': ' + hostname + "][" + dq_status + "] DQ Check")
                    sas_email.set_text_message(sys.stdout.get_log_file_contents())
                    sas_email.send()
        elif email and debug:
            print '[NO EMAIL SENT] Debug is on - will not send email with debug due to possibility of PII.  Turn off debug in the conf file.'
    except Exception as e:
        print '[EXCEPTION]' + str(e)
        exit_value = 2

    shredder = FileShredder(complete_validator_output_file)
    if file_validation_errors:
        exit_value = 2
    procCheck.delete_lock_file()
    sys.exit(exit_value)
