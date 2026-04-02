''' ******************************************************************************
* $Id:$
*
* Copyright(c) 2017 SAS Institute Inc., Cary, NC, USA. All Rights Reserved.
*
* Name: sked.py
*
* Purpose: ssorun like scheduler written in python instead of perl. Consumes xml
*          file schedules and configuration files. See confluence documentation.
*          www.ondemand.sas.com/confluencedoc search for sked
*
* Author: jokich
*
* Support: SAS(r) Solutions OnDemand
*
* Input: -s <schedule>
*        -c <config>
*        -f force flag to start from beginning of schedule
*        -x clear signals related to schedule only
*
* Output:
*
* Parameters: (if applicable)
*
* Dependencies/Assumptions: Configuration file or environmental variables
*
* Usage: Normally compiled for deployment. See confluence documentation.
*
* History:
* 02FEB2017 jokich Initial Code Header Add. See confluence doc for revisions.
****************************************************************************** '''

#import pdb; pdb.Pdb().set_trace()

import sys
import os
import argparse                                   # used for parsing command line arguments
import threading
from collections import namedtuple                # used in schedule data organization
from queue import Queue
from xml.etree.cElementTree import ElementTree    # used to parse xml schedule
from xml.etree.cElementTree import ParseError     # used in parsing schedule try except errortype
from subprocess import Popen, PIPE, DEVNULL       # used to kick off jobs
from time import sleep                            # used to set the polling period of jobs
import datetime                                   # used for time stamps everywhere (logs, stdout, duration, etc)
from contextlib import redirect_stdout            # used to generate log files
import getpass                                    # used to get system user
import configparser                               # used to parse .ini config files
import re                                         # regex functionality
import smtplib                                    # used to send emails
from socket import gethostname                    # used to get the machine name
import signal                                     # contains signal.SIGKILL for terminating jobs immediately
import glob                                       # used to perform a python version of "ls directory/*.suffix.txt" etc
                                                  # used in duration file finding & loading for dependency prioritizing
import traceback                                  # used to output traceback to a file for debugging
from statistics import median, stdev
# import fcntl below in try except logic -- won't work on windows

# sked now pulls the environment variables ("_sked_"-prefixed out of tlchecklist 2016+ standard environment)
# first to determine it's settings. It then fills any gaps with hardcoded defaults. After these are
# set it will try to override these values with any settings found in a configuration file.
# If the user specifies -c on the command line then it's expected that they intend to override (some or all)
# of the settings and sked will error out if it cannot find the config file. Otherwise sked looks relative
# to itself for a ../conf/sked.ini or a sked.ini in the same folder and will override settings values with
# any set in the config file. A config file will always override environment variable values or default values
# (with environment dev/test/prod being the exception if it's already been set by environment variables).

# sys._MEIPASS only exists in pyinstaller compiled version (need to check on other compilers)
# http://pythonhosted.org/PyInstaller/runtime-information.html#using-file-and-sys-meipass
# for pyinstaller use --onefile/-F flag to get single file executable
osenv = dict(os.environ)
if hasattr(sys, '_MEIPASS'):
    sked_packaged = True
    # assumes sked in packaged form will be under a subfolder named 'sked' in the 'bin' folder
    exefile_path = sys.executable

    lp_key = 'LD_LIBRARY_PATH'
    lp_orig = osenv.get(lp_key + '_ORIG')
    if lp_orig is not None:
        osenv[lp_key] = lp_orig  # restore the original, unmodified value
    else:
        # This happens when LD_LIBRARY_PATH was not set.
        # Remove the env var as a last resort:
        osenv.pop(lp_key, None)
else:
    sked_packaged = False
    # assumes sked.pyc will be in the bin folder
    exefile_path = __file__

cwd = os.getcwd()

# Reverse occurence replace function
def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

# windows and linux both work with paths using '/'... use this throughout to take care of any path issues
#sked_path = os.path.realpath(exefile_path).replace(os.path.basename(exefile_path), '').replace('\\', '/')
sked_path = rreplace(os.path.realpath(exefile_path), os.path.basename(exefile_path), '', 1).replace('\\', '/')

pythoncmd = sys.executable
user = getpass.getuser()
on_machine = gethostname()
# print(sked_path)

# Grab command line arguments
parser = argparse.ArgumentParser(description='Run an ETL Schedule')
parser.add_argument('-s', type=str, nargs=1, required=True,
                    help='-s <schedule> specifies a schedule. Required.')
parser.add_argument('-x', action='store_true',
                    help='-x Clears signals only. Does not run schedule.')
parser.add_argument('-n', type=str, nargs=1,
                    help='-n Informs sked that instance called is a sub-schedule. Should not be used manually by user.')
parser.add_argument('-a', type=str, nargs=1,
                    help='-a Gives schedule an alias. Should not be used manually by the user.')
parser.add_argument('-t', action='store_true',
                    help='-t Tests schedule only. Does not run schedule. Will not clear signals.')
parser.add_argument('-f', action='store_true',
                    help='-f Forces a full restart instead of trying to restart')
parser.add_argument('-c', type=str, nargs=1, help='-c Use a specific config file')
parser.add_argument('-r', type=str, nargs=1, help='-r <STDOUT|full path & filename> Report on the status of a schedule')
parser.add_argument('--debug', action='store_true',
                    help='--debug is reserved for future use.')
parser.add_argument('--notifyall', action='store_true',
                    help='--notifyall makes sked send ALL built-in (not custom) email notifications during a run.')
parser.add_argument('-p', type=str, nargs=1,
                    help='-p "parm1=value;thing2=3;also3=valuetoo" specifies passed through parameters that will be ' +
                    'instantiated as $_p_parm1$, $_p_thing2$, $_p_also3$ for keyword replacement')

if os.name == 'posix':
    _ps = '/'
elif os.name == 'win':
    _ps = '\\'
else:
    _ps ='/'

args = parser.parse_args()
filename = args.s[0]
if args.r is not None:
    report_file = args.r[0]
else:
    report_file = None
filenamebase = os.path.basename(filename)
if args.a is not None:
    full_alias = args.a[0]
else:
    full_alias = filenamebase
full_alias_split = full_alias.split('/')
schedule_alias_name = full_alias_split[-1]

signal_clear_only = args.x
if args.n is not None:
    nested_instance = True
    # logfolder = args.n[0] + _ps + filenamebase  # Original functionality pre-schedule_tree.
    schedule_tree = args.n[0].split('|=|')[0] + '/' + filenamebase
    logfolder = args.n[0].split('|=|')[1] + _ps + filenamebase
else:
    nested_instance = False
    schedule_tree = filenamebase
    logfolder = datetime.datetime.now().strftime("%Y%m%d/%H%M%S")

test_schedule_only = args.t
force_full_restart = args.f
debug_mode = args.debug
stop_gracefully = False
notify_all_override = args.notifyall
param_replacements = {}


def stdprint(text):
    if report_file is None:
        print(text)
    elif report_file is not None and report_file != 'STDOUT':
        print(text)
    elif debug_mode:
        with open(os.path.join(cwd, filenamebase + '.stdout'), 'a') as f:
            with redirect_stdout(f):
                print(text)
    else:
        pass
    sys.stdout.flush()

# Used for [User] Config ini variables and command line -p variables
first_validate_problem = 0
param_name_regex = '^[_a-zA-Z0-9-]+$'
param_value_regex = '^[\\\\_a-zA-Z0-9-\,\.:/@#%\^&\*\(\)\+\?\[\]\|\{\}]+$'

def validateUserReplacement(value, type='N'):
    # N = Name of var, V = Value
    if type == 'N':
        match = re.match(param_name_regex, value)
    elif type == 'V':
        match = re.match(param_value_regex, value)
    return match

if args.p is not None:
    # print(args.p[0].split(';'))
    for pair in args.p[0].split(';'):
        # print(pair)
        if validateUserReplacement(pair.split('=')[0].strip()) is not None and \
                        validateUserReplacement(pair.split('=')[1].strip(), type='V') is not None:
            # print('here')
            param_replacements[pair.split('=')[0].strip()] = pair.split('=')[1].strip()
        else:
            if first_validate_problem == 0:
                stdprint('Info: Valid Config [User] or Command Line Parameter (-p) Name Regex: ' + param_name_regex)
                stdprint('Info: Valid Config [User] or Command Line Parameter (-p) Value Regex: ' + param_value_regex)
                first_validate_problem = 1
            if len(pair) > 0 and '=' in pair:
                stdprint('Info: Command Line Parameter name/value will not be used ' +
                         '(contains restricted character): ' + pair.split('=')[0].strip() + '=' +
                         pair.split('=')[1].strip())
            else:
                stdprint('Info: A Command Line Parameter name/value will not be used because it is empty. ' +
                         'This could also be an extra ; on the end of the -p parameter list.')

# default config name
# if os.path.basename(__file__)[:-3] == 'pyc':
#     default_config_filename = os.path.basename(__file__)[:-4] + '.ini'
# elif os.path.basename(__file__)[:-3] == '.py':
#     default_config_filename = os.path.basename(__file__)[:-3] + '.ini'
# else:
#     default_config_filename = 'sked.ini'

if sked_packaged:
    stdprint(os.path.basename(sys.executable) + ' is being run from a packaged executable')
else:
    stdprint(os.path.basename(__file__) + ' is being run natively')
stdprint('sked is running from path: ' + sked_path)

default_config_filename = os.path.splitext(os.path.basename(__file__))[0] + '.ini'
stdprint('sked default config filename to look for: ' + default_config_filename)

# Utility function - read environment variables -- set to none if not found
def getEnv(var, message='Y'):
    try:
        tempvalue = os.environ[var].strip()
        if message == 'Y':
            stdprint('Variable ' + var + ' retrieved from environment.')
    except:
        tempvalue = None
    return tempvalue

# Used for ensure_dir function and replaceEnvVars function for evaluating success
envVarPrefix = '<EnvVar: '


# Utility function to remove non-printable characters from a string
def printable_only(str):
    return re.sub('[\W_]+', '', str)


# Utility function to do replacements on $:<env variable>:$ (e.g. $:USER:$)
def replaceEnvVars(string):
    pattern = r'\$:([a-zA-Z_]{1}[a-zA-Z0-9_]*):\$'
    if string:
        # stdprint(string)
        matched = re.search(pattern, string)
        # stdprint(matched.group(0))
        # stdprint(matched.group(1))
        while(matched != None):
            # stdprint(matched.group(0))
            buildEnvVar = matched.group(1)
            envVar = getEnv(buildEnvVar, message='N')
            if envVar:
                string = string.replace(matched.group(0),envVar)
            else:
                string = string.replace(matched.group(0), envVarPrefix + buildEnvVar + ' not found.>')
            matched = re.search(pattern, string)
        # stdprint(string)
    return string


# Utility function - used for setting default values after env variable read in
def setIfNone(variable_name, variable, value):
    if variable is None:
        stdprint('Variable ' + variable_name + ' set to hardcoded value: ' + value)
        return value.strip()
    else:
        return variable


# Utility function - used for config file value setting
def setIfValue(variable_name, variable, value):
    if value is not None:
        stdprint('From Config File - Setting variable ' + variable_name + ' to ' + value)
        return value.strip()
    else:
        return variable

binsasscriptparams = None
binsasscriptendparams = None
dev_machines = None
tst_machines = None
prd_machines = None
starttls_req = 0
# The rest below are now set to none in the env variable section (if not found) w/getEnv()
# smtp_server = None
# cfgsasrunpath = None
# cfgbinpath = None
# binsasscript = None
# cfgconfpath = None
# cfgsigpath = None
# cfglogpath = None
# machine_in_dev_cycle = None
# sender_email = None
# email_string = None
# plugin_to_load = None

# Placeholders as defaults set below in try/except section
long_running_alerting = 0
long_running_power = 0.9
long_running_min = 1800  # 3600 = 1 hr
long_running_min_times = 8
printStdOut="Off"

# Determine if path has slash on end or not... add if it doesn't
def path_fix(path):
    # stdprint(path)
    if path is not None:
        if path[-1:] != '/':
            path += '/'
        # stdprint(path)
        return path
    else:
        return None

# Pull env variables in or default to None
machine_in_dev_cycle = getEnv('_sked_environment')
cfgsasrunpath = path_fix(getEnv('_sked_sasrunpath'))
cfgbinpath = path_fix(getEnv('_sked_binpath'))
binsasscript = getEnv('_sked_binsasscript')
cfgconfpath = path_fix(getEnv('_sked_confpath'))
cfgsigpath = path_fix(getEnv('_sked_sigpath'))
cfglogpath = path_fix(getEnv('_sked_logpath'))
smtp_server = getEnv('_sked_mailhost')
email_string = getEnv('_sked_recipients')
notify_start = getEnv('_sked_notify_on_schedule_start')
notify_finish = getEnv('_sked_notify_on_schedule_finish')
sender_email = getEnv('_sked_sender_email')
starttls_req = getEnv('_sked_starttls_required')
plugin_to_load = getEnv('_sked_plugin_file')

# Any paths that are None after env, try to guess at the path with some defaults.
if os.name == 'nt':
    # Assumes sked is at bin level
    cfgsasrunpath = setIfNone('cfgsasrunpath', cfgsasrunpath, sked_path + '../sas/programs/')
    cfgbinpath = setIfNone('cfgbinpath', cfgbinpath, sked_path)
    binsasscript = setIfNone('binsasscript', binsasscript, 'C:/Program Files/SASHome/SASFoundation/9.4/sas.exe')
    cfgconfpath = setIfNone('cfgconfpath', cfgconfpath, sked_path + '../conf/')
    cfgsigpath = setIfNone('cfgsigpath', cfgsigpath, sked_path + '../run/signals/')
    cfglogpath = setIfNone('cfglogpath', cfglogpath, sked_path + '../logs/')
elif os.name == 'posix':
    # Assumes sked is at setup level
    cfgsasrunpath = setIfNone('cfgsasrunpath', cfgsasrunpath, sked_path + '../' + user + '/sas/programs/')
    cfgbinpath = setIfNone('cfgbinpath', cfgbinpath, sked_path+'../' + user + '/bin/')
    binsasscript = setIfNone('binsasscript', binsasscript, sked_path + 'ssoaid_startsas.bash')
    cfgconfpath = setIfNone('cfgconfpath', cfgconfpath, sked_path + '../' + user + '/conf/')
    cfgsigpath = setIfNone('cfgsigpath', cfgsigpath, sked_path + '../' + user + '/run/signals/')
    cfglogpath = setIfNone('cfglogpath', cfglogpath, sked_path + '../' + user + '/logs/')

if notify_start is None:
    notify_start = 1
if notify_finish is None:
    notify_finish = 1
if starttls_req is None:
    starttls_req = 0

# Assume there is a config file and set to 0 later
config_file_use = 1
config_file = None
# args.c comes from -c flag where a config file is specified on the command line when calling sked
if args.c is not None:
    if os.path.isabs(args.c[0]) and os.path.isfile(args.c[0]):
        config_file = args.c[0]
    elif os.path.isfile(sked_path + '../conf/' + args.c[0]):
        config_file = sked_path + '../conf/' + args.c[0]
    elif os.path.isfile(sked_path + args.c[0]):
        config_file = sked_path + args.c[0]
    else:
        sys.exit('error: ' + args.c[0] + '  config file cannot be found')
else:  # else no config file specified -- guess at locations where it might be
    # Pull in schedule if exists and override any values that are found
    if os.path.isfile(sked_path + '../conf/' + default_config_filename):  # check for conf directory
        config_file = sked_path + '../conf/' + default_config_filename
        stdprint('config file found: ' + config_file)
    elif os.path.isfile(sked_path + default_config_filename):  # check directory scheduler in
        config_file = sked_path + default_config_filename
        stdprint('config file found: ' + config_file)
    else:  # config file wasn't found - keep defaults/env values set above
        config_file_use = 0
        stdprint('Info: No config file found. Will use default paths and values or environment variables.')
        '''
        if os.name == 'nt':
            #stdprint('config file: <Using windows default testing paths>')
            #sasrunpath - where sas run programs exist
            #cfgsasrunpath=sked_path+'../sas/programs/'
            #binpath - where shell scripts/programs exist
            #cfgbinpath=sked_path
            #binsasscript - full path to sas executable or sas shell script
            #binsasscript='C:/Program Files/SASHome/SASFoundation/9.4/sas.exe'
            #confpath - where schedules live
            #cfgconfpath=sked_path+'../conf/'
            #sigpath - where signals live
            #cfgsigpath=sked_path+'../run/signals/'
            #logpath - where logging should be directed for scheduler -- does not control where sas logs go
            #cfglogpath=sked_path+'../logs/'

            cfgsasrunpath = setIfNone('cfgsasrunpath', cfgsasrunpath, sked_path + '../sas/programs/')
            cfgbinpath = setIfNone('cfgbinpath', cfgbinpath, sked_path)
            binsasscript = setIfNone('binsasscript', binsasscript, 'C:/Program Files/SASHome/SASFoundation/9.4/sas.exe')
            cfgconfpath = setIfNone('cfgconfpath', cfgconfpath, sked_path + '../conf/')
            cfgsigpath = setIfNone('cfgsigpath', cfgsigpath, sked_path + '../run/signals/')
            cfglogpath = setIfNone('cfglogpath', cfglogpath, sked_path + '../logs/')
        elif os.name=='posix':
            #stdprint('config file: <Using linux default testing paths> - may not be correct')
            #setIfNone_msg = 'config file: <Using linux default testing paths> - may not be correct'
            cfgsasrunpath = setIfNone('cfgsasrunpath', cfgsasrunpath, sked_path+'../sas/programs/')
            #cfgsasrunpath=sked_path+'../sas/programs/'
            cfgbinpath = setIfNone('cfgbinpath', cfgbinpath, sked_path)
            #cfgbinpath=sked_path
            binsasscript = setIfNone('binsasscript', binsasscript, sked_path+'ssoaid_startsas.bash')
            #binsasscript=sked_path+'ssoaid_startsas.bash'
            cfgconfpath = setIfNone('cfgconfpath', cfgconfpath, sked_path+'../conf/')
            #cfgconfpath=sked_path+'../conf/'
            cfgsigpath = setIfNone('cfgsigpath', cfgsigpath, sked_path+'../run/signals/')
            #cfgsigpath=sked_path+'../run/signals/'
            cfglogpath = setIfNone('cfglogpath', cfglogpath, sked_path+'../logs/')
            #cfglogpath=sked_path+'../logs/'
            #cfgbinsasscriptparams=None
        '''

# Parse config in sections due to different information being needed at different times.
# (a few config_file_use if statements below)
user_specific_replacements = {}   # Declared here instead of below -- so environments w/o config file work.
if config_file_use == 1:
    # This function likely not used anymore -- fallback values don't work through it
    '''
    def ConfigSectionMap(section):
        dict1 = {}
        options = Config.options(section)
        for option in options:
            try:
                #example: Config.get('Notifications', 'notification_on_schedule_start', fallback=None)
                dict1[option] = Config.get(section, option)
                #dict1[option] = Config.get(section, option, fallback=None)
                if dict1[option] == -1:
                    stdprint("skip: %s" % option)
            except:
                #stdprint("exception on %s!" % option)
                dict1[option] = None
        return dict1
    '''

    Config = configparser.ConfigParser()
    Config.read(config_file)

    if 'User' in Config.sections() and len(Config['User']) != 0:
        for item in Config['User']:
            if validateUserReplacement(item.strip()) is not None and \
                            validateUserReplacement(Config['User'][item].strip(), type='V') is not None:
                user_specific_replacements[item] = Config['User'][item]
            else:
                if first_validate_problem == 0:
                    stdprint('Info: Valid Config [User] or Command Line Parameter (-p) Name Regex: ' + param_name_regex)
                    stdprint('Info: Valid Config [User] or Command Line Parameter (-p) Value Regex: ' + param_value_regex)
                    first_validate_problem = 1
                stdprint('Info: Config.ini [User] Parameter name/value will not be used ' +
                         '(contains restricted character): ' + item + '=' + Config['User'][item])
            # print(item, ' = ', Config['User'][item])
            # print(Config['User'][item])

    # cfgbinsasscript = ConfigSectionMap("Paths")['binsasscript']

    # ----------------------------------
    cfgbinsasscript = Config.get('Paths', 'binsasscript', fallback=None)
    # jazzha: a new .ini variable in the General section that determine printing of stdout for normal execution
    printStdOut = Config.get('General', 'printStdOut', fallback="Off")
    binsasscriptparams = replaceEnvVars(Config.get('Paths', 'binsasscriptparams', fallback=None))
    binsasscriptendparams = replaceEnvVars(Config.get('Paths', 'binsasscriptendparams', fallback=None))

    if binsasscriptparams is not None:
        binsasscriptparams = binsasscriptparams.replace('$logfolder$', logfolder)
        binsasscriptparams = binsasscriptparams.replace('$scheduletree$', schedule_tree)
    if binsasscriptendparams is not None:
        binsasscriptendparams = binsasscriptendparams.replace('$logfolder$', logfolder)
        binsasscriptendparams = binsasscriptendparams.replace('$scheduletree$', schedule_tree)

    # Utility function to call path_fix function and replace $user$ token.
    # -- The only token available at this point that makes sense to utilize
    def rsvl_keytkns(path,do_path_fix='Y'):
        # Make sure path ends in separator - required for checking directory existence
        if path is not None:
            if do_path_fix == 'Y':
                path = path_fix(path)
            # Key Token Replacements
            return replaceEnvVars(path.replace('$user$', user))
        else:
            return None

    # cfgbinpath = rsvl_keytkns(ConfigSectionMap("Paths")['binpath'])
    cfgbinpath = setIfValue('cfgbinpath [from .ini]',
                            cfgbinpath,
                            rsvl_keytkns(Config.get('Paths', 'binpath', fallback=None)))
    # cfgconfpath=rsvl_keytkns(ConfigSectionMap("Paths")['confpath'])
    cfgconfpath = setIfValue('cfgconfpath [from .ini]',
                             cfgconfpath,
                             rsvl_keytkns(Config.get('Paths', 'confpath', fallback=None)))
    # cfgsasrunpath=rsvl_keytkns(ConfigSectionMap("Paths")['sasrunpath'])
    cfgsasrunpath = setIfValue('cfgsasrunpath [from .ini]',
                               cfgsasrunpath,
                               rsvl_keytkns(Config.get('Paths', 'sasrunpath', fallback=None)))
    # cfgsigpath=rsvl_keytkns(ConfigSectionMap("Paths")['sigpath'])
    cfgsigpath = setIfValue('cfgsigpath [from .ini]',
                            cfgsigpath,
                            rsvl_keytkns(Config.get('Paths', 'sigpath', fallback=None)))
    # cfglogpath=rsvl_keytkns(ConfigSectionMap("Paths")['logpath'])
    cfglogpath = setIfValue('cfglogpath [from .ini]',
                            cfglogpath,
                            rsvl_keytkns(Config.get('Paths', 'logpath', fallback=None)))
    # binsasscript=rsvl_keytkns(cfgbinsasscript,do_path_fix='N')
    binsasscript = setIfValue('binsasscript [from .ini]',
                              binsasscript,
                              rsvl_keytkns(cfgbinsasscript,do_path_fix='N'))

# Check to make sure binsasscript exists
if binsasscript is None or not os.path.exists(binsasscript):
    if binsasscript is None:
        sys.exit('error: binsasscript is not set in config')
    else:
        sys.exit('error: ' + binsasscript + ' (binsasscript) does not exist.')
# binsasscript = os.path.realpath(os.path.normpath(binsasscript)) # Not needed -- was testing for flock/symlink issue

# Utility function - check that path exists, if signal path or log path doesn't exist create it. Throw error
# if other paths don't exist.
def ensure_dir(f, dirname):
    if f is not None:
        d = os.path.dirname(f)
        if not os.path.exists(d):
            if f == cfgsigpath or f == cfglogpath:
                if envVarPrefix not in f:
                    os.makedirs(d)
                else:
                    sys.exit('error: directory environment variable not resolved: ' + f)
            else:
                sys.exit('error: directory not found. tried: ' + f + ' required for running')
        # f = os.path.realpath(os.path.normpath(f)) + '/'  # Not needed -- was testing for flock/symlink issue
    else:
        sys.exit('error: directory not found ' + dirname + ' required for running')
    return f

binpath = ensure_dir(cfgbinpath, 'Bin path')
sasrunpath = ensure_dir(cfgsasrunpath, 'Run path')
# binsasscript=ensure_dir(cfgbinsasscript)
confpath = ensure_dir(cfgconfpath, 'Conf path')
sigpath = ensure_dir(cfgsigpath, 'Signal path')
logpath = ensure_dir(cfglogpath, 'Log path')

# stdprint('sasrunpath: ' + sasrunpath)
# stdprint('binpath: ' + binpath)
# stdprint('confpath: ' + confpath)

# Setup logging/print to file
log_file_name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_")+os.path.basename(exefile_path)+'_'+os.path.basename(filename)+'.log'
prse_log_file_name = log_file_name+'.psv'
suffix_to_find = '_' + os.path.basename(filename) + '.times.psv'
log_file_name_times = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_")+os.path.basename(exefile_path)+suffix_to_find
stdout_file_name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_")+os.path.basename(exefile_path)+'_'+os.path.basename(filename)+'.stdout'


# Utility function for loggin to print out to a log file.
def print2(y, log_file_nm=log_file_name, reg_print=True):
    if reg_print and (report_file is None or report_file != 'STDOUT'):
        print(y)
    with open(logpath+log_file_nm, 'a') as f:
        with redirect_stdout(f):
            print(y)
    sys.stdout.flush()


# For capturing any standard out during a schedule run.
def stdout_print(y):
    with open(logpath+stdout_file_name, 'a') as wr_std_out:
        with redirect_stdout(wr_std_out):
            print(y)
    sys.stdout.flush()


# Utility function for logging. .psv (pipe separated values) parseable log output
def prselogprint(dttime=None,
                 level = 'Job',
                 level2 = None, # In reality this isn't used much and is more of a placeholder.
                 status = None,
                 fullrunfile = None,
                 name_alias = None,
                 ops_label = None,
                 message = None
                 ):
    if dttime is not None:
        logline = dttime + '|'
    else:
        logline = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '|'
    logline += level + '|'
    if level2 is not None:
        logline += level2
    logline += '|'
    if status is not None:
        logline += status
    logline += '|'
    if fullrunfile is not None:
        logline += fullrunfile
    logline += '|'
    if name_alias is not None:
        logline += name_alias
    logline += '|'
    if ops_label is not None:
        logline += ops_label
    logline += '|'
    if message is not None:
        logline += message
    print2(logline, log_file_nm=prse_log_file_name, reg_print=False)


# Put a header record in the parseable log
prselogprint(dttime='date time',
             level='level',
             level2='level2',
             status='status',
             fullrunfile='fullrunfile',
             name_alias='name_alias',
             ops_label='ops_label',
             message='message'
             )

if args.a is not None:
    print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
           'Info: Parent schedule alias/filename for this schedule: ' + schedule_alias_name)

if test_schedule_only:
    print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Info: Test schedule only flag set (-t).')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Info',
                 fullrunfile=filename,
                 ops_label=None,
                 message='Test schedule only flag set (-t).'
                 )

# Utility function for logging durations. .psv (pipe separated values) parseable log output
def durprint(name='default', duration=0):
    logline = name + '|' + str(duration)
    print2(logline, log_file_nm=log_file_name_times, reg_print=False)

# More config read in for email notifications and dev/test/prod machine read in
cfg_scheduletype_errors = 'Y'
if config_file_use == 1:
    # notify_start=Config.get('Notifications', 'notification_on_schedule_start', fallback=None)
    notify_start = setIfValue('notification_on_schedule_start [from .ini]',
                              notify_start,
                              Config.get('Notifications', 'notification_on_schedule_start', fallback=None))
    # notify_finish=Config.get('Notifications', 'notification_on_schedule_finish', fallback=None)
    notify_finish = setIfValue('notification_on_schedule_finish [from .ini]',
                               notify_finish,
                               Config.get('Notifications', 'notification_on_schedule_finish', fallback=None))
    # smtp_server=Config.get('Notifications', 'mailhost', fallback=None)
    # ConfigSectionMap("Notifications")['mailhost']
    smtp_server = replaceEnvVars(setIfValue('smtp_server [from .ini]',
                             smtp_server,
                             Config.get('Notifications', 'mailhost', fallback=None)))
    # email_string = Config.get('Notifications', 'recipients', fallback=None)
    # ConfigSectionMap("Notifications")['recipients']
    email_string = setIfValue('email_string [from .ini]',
                              email_string,
                              Config.get('Notifications', 'recipients', fallback=None))

    starttls_req = setIfValue('starttls_required [from .ini]',
                              starttls_req,
                               Config.get('Notifications', 'starttls_required', fallback=None))


    cfg_scheduletype_errors = Config.get('Notifications', 'schedule_type_error_emails', fallback='Y')

    if email_string is not None:
        email_string = replaceEnvVars(email_string.replace('$user$', user))

    # This should be redundant at this point. Keeping just in case.
    if notify_start is None:
        notify_start = 1
    if notify_finish is None:
        notify_finish = 1
    if starttls_req is None:
        starttls_req = 0

    # sender_email = Config.get('Notifications', 'sender_email', fallback=None)
    sender_email = replaceEnvVars(setIfValue('sender_email [from .ini]',
                              sender_email,
                              Config.get('Notifications', 'sender_email', fallback=None)))

    if machine_in_dev_cycle is None:
        dev_machines = replaceEnvVars(Config.get('Machines', 'dev_hostnames', fallback=None))
        tst_machines = replaceEnvVars(Config.get('Machines', 'test_hostnames', fallback=None))
        prd_machines = replaceEnvVars(Config.get('Machines', 'prod_hostnames', fallback=None))
'''
else:
    notify_start=0
    notify_finish=0
    smtp_server=None
    email_string=None
'''

# If machine_in_dev_cycle isn't set from env try to figure out whether it's dev/test/prod.
# Note that dev/test/prod is the limit of guessing in sked and that pulling in env variables can have limitless names
if machine_in_dev_cycle is None:
    on_machine_email = on_machine
    if dev_machines is not None and on_machine in dev_machines:
        machine_in_dev_cycle = 'dev'
        # on_machine_email = 'DEV (' + on_machine +')'
    if machine_in_dev_cycle is None and tst_machines is not None and on_machine in tst_machines:
        machine_in_dev_cycle = 'test'
        # on_machine_email = 'TEST (' + on_machine + ')'
    if machine_in_dev_cycle is None and prd_machines is not None and on_machine in prd_machines:
        machine_in_dev_cycle = 'prod'
        # on_machine_email = 'PROD (' + on_machine + ')'

# If machine_in_dev_cycle gets set, setup emails to display
if machine_in_dev_cycle is not None:
    on_machine_email = machine_in_dev_cycle.upper() + ' (' + on_machine + ')'
else:
    on_machine_email = on_machine

# More config file read in -- max_concurrent_jobs setting and plugins
if config_file_use == 1:
    max_concurrent_jobs = Config.get('General', 'max_concurrent_jobs', fallback=999)
    try:
        max_concurrent_jobs = int(max_concurrent_jobs)
        if max_concurrent_jobs < 0:
            max_concurrent_jobs = 999
    except:
        max_concurrent_jobs = 999
    max_concurrent_jobs = round(max_concurrent_jobs)
    if max_concurrent_jobs < 1:
        max_concurrent_jobs = 1
    # plugin_to_load = Config.get('General', 'plugin', fallback=None)
    plugin_to_load = setIfValue('plugin [from .ini]', plugin_to_load,
                                rsvl_keytkns(Config.get('General', 'plugin', fallback=None), do_path_fix='N'))

    holiday_file = Config.get('General', 'holiday_file', fallback=None)

    optimize_concurrency = Config.get('General', 'optimize_concurrency', fallback=1)
    optimize_concurrency_files = Config.get('General', 'optimize_concurrency_files', fallback=8)

    long_running_alerting = Config.get('General', 'long_running_alerting', fallback=0)
    long_running_min_times = Config.get('General', 'long_running_min_times', fallback=8)
    long_running_min = Config.get('General', 'long_running_min', fallback=1800)
    long_running_power = Config.get('General', 'long_running_power', fallback=0.9)

    print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Info: Config File Utilized: ' + config_file)
    prselogprint(level='Schedule',
                 level2=None,
                 status='Info',
                 fullrunfile=filename,
                 ops_label=None,
                 message='Config File Utilized: ' + config_file
                 )
else:
    max_concurrent_jobs = 999
    optimize_concurrency = 1
    optimize_concurrency_files = 8
    holiday_file = None

try:
    notify_start = int(notify_start)
    notify_finish = int(notify_finish)
except:
    notify_start = 1
    notify_end = 1
    print2(
        datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S - ") + 'Info: Notification on start/finish is ' +
                                                                   'not integer. Default to 1')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Info',
                 fullrunfile=filename,
                 ops_label=None,
                 message='Notification on start/finish is not integer. Default to 1'
                 )
try:
    starttls_req = int(starttls_req)
except:
    starttls_req = 0
    print2(
        datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S - ") + 'Info: starttls_required is ' +
        'not integer. Default to 0')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Info',
                 fullrunfile=filename,
                 ops_label=None,
                 message='starttls_required is not integer. Default to 0'
                 )

try:
    optimize_concurrency = int(optimize_concurrency)
except:
    optimize_concurrency = 0
try:
    optimize_concurrency_files = int(optimize_concurrency_files)
    if optimize_concurrency_files < 0:
        optimize_concurrency_files = 8
except:
    optimize_concurrency_files = 8
try:
    long_running_alerting = int(long_running_alerting)
except:
    long_running_alerting = 0
try:
    long_running_power = float(long_running_power)
except:
    long_running_power = 0.9
try:
    long_running_min_times = int(long_running_min_times)
except:
    long_running_min_times = 8
try:
    long_running_min = int(long_running_min)
except:
    long_running_min = 1800

# print(long_running_alerting)
# print(long_running_power)
# print(long_running_min)
# print(long_running_min_times)

# ---------------------------------------------------------------------------------------------------------------------

# If there is a plugin specified in the config file check the existence of the file. Error out if it doesn't exist.
# If it exists, load the plugin so it's functions can be accessed.
if plugin_to_load is not None:
    plugin_to_load = replaceEnvVars(plugin_to_load)
    if os.path.isabs(plugin_to_load):
        if os.path.exists(plugin_to_load):
            plugin_error = 0
        else:
            plugin_error = 1
    else:
        if os.path.exists(confpath+plugin_to_load):
            plugin_to_load = confpath + plugin_to_load
            plugin_error = 0
        else:
            plugin_error = 1
    if plugin_error == 1:
        print2(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Error: Plugin not found: ' + plugin_to_load)
        prselogprint(level='Schedule',
                     level2=None,
                     status='Error',
                     fullrunfile=filename,
                     ops_label=None,
                     message='Plugin not found: ' + plugin_to_load
                     )
        sys.exit('Error: plugin specified but not found')
    else:
        print2(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Info: Plugin found: ' + plugin_to_load)
        prselogprint(level='Schedule',
                     level2=None,
                     status='Info',
                     fullrunfile=filename,
                     ops_label=None,
                     message='Plugin found: ' + plugin_to_load
                     )
    import importlib.util
    plugin_spec = importlib.util.spec_from_file_location("sked_plugin.name", plugin_to_load)
    sked_plugin = importlib.util.module_from_spec(plugin_spec)
    plugin_spec.loader.exec_module(sked_plugin)

# If a holiday file exists go ahead and check here if the rest of the schedule should run. If not exit and log.
if holiday_file is not None:
    holiday_file = replaceEnvVars(holiday_file)
    if os.path.isabs(holiday_file):
        if os.path.exists(holiday_file):
            holiday_file_err = 0
        else:
            holiday_file_err = 1
    else:
        if os.path.exists(confpath + holiday_file):
            holiday_file = confpath + holiday_file
            holiday_file_err = 0
        else:
            holiday_file_err = 1
    if holiday_file_err == 1:
        print2(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Error: Holiday File not found: ' + holiday_file)
        prselogprint(level='Schedule',
                     level2=None,
                     status='Error',
                     fullrunfile=filename,
                     ops_label=None,
                     message='Holiday File not found: ' + holiday_file
                     )
        sys.exit('Error: Holiday File specified but not found.')
    else:
        print2(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Info: Holiday File found: ' + holiday_file)
        prselogprint(level='Schedule',
                     level2=None,
                     status='Info',
                     fullrunfile=filename,
                     ops_label=None,
                     message='Holiday File found: ' + holiday_file
                     )
    holiday_list = []
    with open(holiday_file, 'r') as holiday_file_content:
        for line in holiday_file_content:
            # line = line.replace('\n','')
            line = printable_only(line)
            try:
                holiday_list.append(datetime.datetime.strptime(line, "%d%b%Y"))
            except:
                print2(
                    datetime.datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S - ") + 'Info: Holiday File: Could not read in line: ' + line)
                prselogprint(level='Schedule',
                             level2=None,
                             status='Info',
                             fullrunfile=filename,
                             ops_label=None,
                             message='Holiday File: Could not read in line: ' + line
                             )
    today = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0))
    if today in holiday_list:
        print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
               'Exit: Bypassed Schedule - Today is in holiday file')
        prselogprint(level='Schedule',
                     level2=None,
                     status='Bypassed',
                     fullrunfile=None,
                     ops_label=None,
                     message='Today is in holiday file'
                     )
        sys.exit('Finished: Today is in the holiday file')


# find previous run time files and load into dictionary
# logpath + '*' + suffix_to_find
#  There is no intention of advanced features such as piecing together durations from the last 6 instances
#  in which sked ran because of 5 job errors that occurred in the last full schedule run through. This would
#  be not only difficult to track but could potentially not be indicative of a normal run.
avg_past_duration = {}
times_per_jobs = {}
max_past_duration = {}
min_past_duration = {}
all_durations = {}
stdev_duration = {}
median_duration = {}

if optimize_concurrency is not None and optimize_concurrency == 1 and test_schedule_only is False and \
                signal_clear_only is False:
    prev_dur_file_list = [os.path.basename(x) for x in glob.glob(logpath + '*' + suffix_to_find)]
    num_dur_files = len(prev_dur_file_list)
    if num_dur_files > 0:  # If one or more past timing files are available
        try:
            prev_dur_file_list.sort(reverse=True)  # sort the files (filename includes dates)
            if long_running_alerting == 0:
                long_running_min_times = 0
            for durfile in range(0, min(num_dur_files, max(optimize_concurrency_files, long_running_min_times))):
                with open(logpath + prev_dur_file_list[durfile]) as f:
                    for l in f:
                        durfilejob = l.strip().split("|")[0]
                        durvalue = int(l.strip().split("|")[1])
                        if durfilejob in all_durations:
                            times_per_jobs[durfilejob] += 1
                            avg_past_duration[durfilejob] += durvalue
                            max_past_duration[durfilejob] = max(max_past_duration[durfilejob],
                                                                durvalue)
                            min_past_duration[durfilejob] = min(max_past_duration[durfilejob],
                                                                durvalue)
                            all_durations[durfilejob].append(durvalue)
                        else:
                            times_per_jobs[durfilejob] = 1
                            avg_past_duration[durfilejob] = durvalue
                            max_past_duration[durfilejob] = durvalue
                            min_past_duration[durfilejob] = durvalue
                            all_durations[durfilejob] = []
                            all_durations[durfilejob].append(durvalue)

            for key in avg_past_duration:
                avg_past_duration[key] = avg_past_duration[key] / times_per_jobs[key]
                all_durations[key].sort()
                stdev_duration[key] = stdev(all_durations[key])
                median_duration[key] = median(all_durations[key])

            # stdprint(avg_past_duration)
            '''
            most_cur_dur_file = prev_dur_file_list[1]  # grab last item in list (or most current duration file)
            with open(logpath + most_cur_dur_file) as f:
                for l in f:
                    avg_past_duration[l.strip().split("|")[0]] = int(l.strip().split("|")[1])  # read into dictionary
            '''

            print2(
                datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S - ") + 'Info: Previous job duration file(s) read in')
            prselogprint(level='Schedule',
                         level2=None,
                         status='Info',
                         fullrunfile=filename,
                         ops_label=None,
                         message='Previous job duration file read in'
                         )
        except:
            print2(
                datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S - ") + 'Info: Previous job duration file(s) present but unable to read in')
            prselogprint(level='Schedule',
                         level2=None,
                         status='Info',
                         fullrunfile=filename,
                         ops_label=None,
                         message='Previous job duration file(s) present but unable to read in'
                         )
else:
    long_running_alerting = 0


# Utility function - validate emails with regex
# https://www.lifewire.com/are-email-addresses-case-sensitive-1171111
# sked allows capital letters in emails
def validate_email(email_here):
    match = re.match('^[_a-zA-Z0-9-]+(\.[_a-zA-Z0-9-]+)*@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*(\.[a-zA-Z]{2,4})$', email_here)
    if match is None:
        print2(
            datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S - ") + 'Info: ' + email_here +
            ' does not appear to be a valid email. Will bypass utilizing this email.')
        prselogprint(level='Schedule',
                     status='Info',
                     message=email_here + ' does not appear to be a valid email. Will bypass utilizing this email'
                     )
    return match

# Validate sending email
if sender_email is not None and validate_email(sender_email) is None:
    sender_email = None


# Utility function - take email string and split on comma separated emails, check each one, return list
def email_string_to_list(email_string):
    recipients_checked = []
    if email_string is not None:
        recipients = email_string.split(',')
        for recipient in recipients:
            if validate_email(recipient.strip()) is not None:
                recipients_checked.append(recipient.strip())
    return recipients_checked

# Build recipient list based on utility function
recipients_checked = email_string_to_list(email_string)

# Flag to no longer try to send emails if first email attempt fails.
suppress_further_emails = 0


# Handle starttls if needed in one place
def send_email_type(send_from, send_to, message):
    if suppress_further_emails == 0:
        try:
            session = smtplib.SMTP(smtp_server)
            session.ehlo()
            if starttls_req == 1:
                session.starttls()
                session.ehlo()
            session.sendmail(send_from, send_to, message)
            session.quit()
            return 0
        except:
            stdout_print(traceback.format_exc())
            print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Info: Unable to send email ' +
                   'notification with current settings. Check mailhost and whether or not tls is required. Further ' +
                   'email attempts will be limited. If no emails desired -- remove mailhost completely.')
            prselogprint(level='Schedule',
                     level2=None,
                     status='Info',
                     fullrunfile=x.runfile,
                     ops_label=None,
                     message='Unable to send email notifications with current settings. Check mailhost and whether ' +
                             'or not tls is required. Further email attempts will be limited. If no emails desired ' +
                             '-- remove mailhost completely.'
                     )
            return 99


# Email Notification Function
# For an email to be sent, mailhost and recipients must exist, sender_email will be defaulted if not specified.
def send_email_notify(subject, body):
    erc = suppress_further_emails
    if smtp_server is not None and len(recipients_checked) > 0:
        if sender_email is None:
            sender = os.path.basename(exefile_path) + '@' + on_machine
        else:
            sender = sender_email
        # message = 'Subject: '+ subject + '\n\n' + body  # original message had no To in received emails
        message = 'To: ' + ','.join(recipients_checked) + '\nSubject: ' + subject + '\n\n' + body
        erc = send_email_type(sender, recipients_checked, message)
    return erc


# Function to take care of keyword replacements for the rest of sked
def createReplacements(string, x, allow_breaks='N'):
    # runfile.replace('$user$', user)
    if x is not None:
        string = string.replace('$runfiletype$', x.runfiletype)
        string = string.replace('$runfiletype_UP$', x.runfiletype.upper())
        string = string.replace('$jobname$', sch_st_key(x))
        string = string.replace('$jobname_UP$', sch_st_key(x).upper())

    string = string.replace('$user$', user)
    string = string.replace('$user_UP$', user.upper())
    string = string.replace('$logfolder$', logfolder)
    string = string.replace('$scheduletree$', schedule_tree)
    string = string.replace('$filenamebase$', filenamebase)
    if machine_in_dev_cycle is not None:
        string = string.replace('$env$', machine_in_dev_cycle)
        string = string.replace('$env_UP$', machine_in_dev_cycle.upper())
    string = string.replace('$hostname$', on_machine)
    string = string.replace('$hostname_UP$', on_machine.upper())

    # From ini/env/defaults:
    string = string.replace('$binsasscript$', binsasscript)
    string = string.replace('$confpath$', confpath)
    string = string.replace('$binpath$', binpath)
    string = string.replace('$sigpath$', sigpath)
    string = string.replace('$logpath$', logpath)
    string = string.replace('$runpath$', sasrunpath)
    string = string.replace('$programpath$', sasrunpath)

    for u_item in user_specific_replacements:
        string = string.replace('$_u_' + u_item.replace(' ','_') + '$', user_specific_replacements[u_item])

    for p_item in param_replacements:
        string = string.replace('$_p_' + p_item.replace(' ','_') + '$', param_replacements[p_item])

    if allow_breaks == 'Y':
        string = string.replace('$n$', '\n')
        string = string.replace('$nn$', '\n\n')
        string = string.replace('$nnn$', '\n\n\n')

    # Take care of environment variables here to cover schedule & custom email inis
    string = replaceEnvVars(string)

    return string


# Allow custom emails per job
# Time variables not used, reserved for later
def send_email_notify_custom(x, which_email, start_time=None, end_time=None):
    # stdprint('Entering Custom Email Function (send_email_notify_custom()) - ' + x.runfile + ' - ' + which_email)
    erc = suppress_further_emails
    if x.email_ini is not None:
        # stdprint('x.email_ini in schedule (send_email_notify_custom()) - ' + x.runfile + ' - ' + which_email)
        if not os.path.isfile(cfgconfpath + x.email_ini):
            print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Error: Custom email ini ' \
                   + cfgconfpath + x.email_ini + ' doesn\'t exist')
            prselogprint(level='Schedule',
                         level2=None,
                         status='Error',
                         fullrunfile=x.runfile,
                         ops_label=None,
                         message='Custom email ini ' + cfgconfpath + x.email_ini + ' doesn\'t exist'
                         )
        emConfig = configparser.ConfigParser()
        emConfig.read(cfgconfpath + x.email_ini)

        # If notify=1 not in config.ini, send_email_yn comes back None which is an indicator that the whole
        # section or file isn't present.
        send_email_yn = emConfig.get(which_email, 'notify', fallback=None)
        if send_email_yn is None:
            print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Info: Custom email ini ' \
                   + x.email_ini + ' either isn\'t found or doesn\'t have notify set for this group (' \
                   + which_email + ')')
            prselogprint(level='Schedule',
                         level2=None,
                         status='Info',
                         fullrunfile=x.runfile,
                         ops_label=None,
                         message=x.email_ini + ' either isn\'t found or doesn\'t have notify set for this group (' \
                         + which_email + ')'
                         )
        elif send_email_yn == '1':
            # stdprint('send_email_yn == 1 (send_email_notify_custom()) - ' + x.runfile + ' - ' + which_email)
            recipients_str = emConfig.get(which_email, 'recipients', fallback=None)
            sender = emConfig.get(which_email, 'sender', fallback=None)
            subject = emConfig.get(which_email, 'subject', fallback=None)
            body = emConfig.get(which_email, 'body', fallback=None)

            recipients_checked2 = []
            if recipients_str is not None:
                recipients_checked2 = email_string_to_list(createReplacements(recipients_str.strip(), x))
            if sender is not None:
                sender = createReplacements(sender.strip(), x)
                if validate_email(sender) is None:
                    sender = None

            # stdprint('Recipients: ' + recipients_str + ' (send_email_notify_custom()) - ' + x.runfile + ' - ' + which_email)
            # stdprint(recipients_checked2)
            # stdprint('Sender: ' + sender + ' (send_email_notify_custom()) - ' + x.runfile + ' - ' + which_email)

            if smtp_server is not None \
                    and len(recipients_checked2) > 0 \
                    and sender is not None \
                    and body is not None \
                    and subject is not None:
                # stdprint('Trying to send email (send_email_notify_custom()) - ' + x.runfile + ' - ' + which_email)
                body = createReplacements(body, x, allow_breaks='Y')
                subject = createReplacements(subject.strip(), x)

                # message = 'Subject: ' + subject + '\n\n' + body  # original message had no To in received emails
                message = 'To: ' + ','.join(recipients_checked2) + '\nSubject: ' + subject + '\n\n' + body
                erc = send_email_type(sender, recipients_checked2, message)
    return erc

# jobs_run holds jobs that have kicked off already in the schedule. Set way up here so functions will recognize it and
# not say it's not declared. (PyCharm IDE aggravation)
jobs_run = []

# errored_jobs holds jobs that have kicked off already and failed. Set way up here so functions will recognize it and
# not say it's not declared. (PyCharm IDE aggravation)
errored_jobs = []

# Helper function to determine whether or not to use name_alias or runfile for status key
def sch_st_key(jentry):
    if jentry.name_alias is None:
        schedule_status_key = jentry.runfile
    else:
        schedule_status_key = jentry.name_alias
    return schedule_status_key


# Signal functions
def signal_wrapper(jentry, jstatus, jfunction, return_code='n'):
    signal_name = filenamebase + '_' + sch_st_key(jentry)
    signal_name = signal_name + '-' + jstatus + '.sig'
    if return_code != 'y':
        jfunction(signal_name)
    else:
        return jfunction(signal_name)


# Note that signal contents writing is append. This is on purpose to support ops team so that the latest start time
# is in a single signal.
def place_signal(sname, write_in='y'):
    with open(sigpath+sname, 'a') as signal_file:
        if write_in == 'y':
            signal_file.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '|' + log_file_name + '|' +
                              prse_log_file_name + '\n')


def place_signal_job(jentry, jstatus):
    signal_wrapper(jentry, jstatus, place_signal)


def remove_signal(sname):
    os.remove(sigpath + sname)


def remove_signal_job(jentry, jstatus):
    signal_wrapper(jentry, jstatus, remove_signal)


def exist_signal(sname):
    if os.path.isfile(sigpath + sname):
        return True
    else:
        return False


def exist_del_signal(sname):
    if exist_signal(sname):
        remove_signal(sname)


def existrem_signal_job(jentry,jstatus):
    signal_wrapper(jentry, jstatus, exist_del_signal)


def exist_signal_job(jentry, jstatus):
    return signal_wrapper(jentry, jstatus, exist_signal, return_code='y')


# If tempstop present then exit without doing anything further.
# Will also check for this during schedule run.
if exist_signal(filenamebase+'_TEMPSTOP.txt') or exist_signal('sked_TEMPSTOP.txt'):
    stdprint(filenamebase + '_TEMPSTOP.txt or sked_TEMPSTOP.txt signal is present. Exiting. Remove it to continue.')
    sys.exit(0)


# Utility function for unknown file types (sas, shell, schedule are acceptable types as of 2016/08/22)
def error_UnknownFiletype(x):
    print2('error: Unknown filetype found - filetype: ' + x.runfiletype + ' - please check schedule: ' + filename)
    prselogprint(level='Schedule',
                 level2=None,
                 status='Error',
                 fullrunfile=x.runfile,
                 ops_label=None,
                 message='Unknown filetype found - filetype: ' + x.runfiletype + ' - please check schedule xml'
                 )


# Build full file paths and names for verification and run commands
def comp_runfile(y):
    # c_runfile = '' # This will always be set. Setting here is redundant.
    if y.runfiletype.lower() != 'dependency_collection':
        if os.path.isabs(y.runfile):
            if y.runfiletype.lower() not in ['sas', 'shell', 'schedule']:
                error_UnknownFiletype(y)
                c_runfile = 'error: unknown filetype found - filetype: ' + y.runfiletype + ' - please check schedule: ' + filename
            else:
                c_runfile = y.runfile
        else:
            if y.runfiletype.lower() == 'sas':
                c_runfile = sasrunpath + y.runfile
            elif y.runfiletype.lower() == 'shell':
                c_runfile = binpath + y.runfile
            elif y.runfiletype.lower() == 'schedule':
                c_runfile = confpath + y.runfile
            else:
                error_UnknownFiletype(y)
                c_runfile = 'error: unknown filetype found - filetype: ' + y.runfiletype + \
                            ' - please check schedule: ' + filename
        c_runfile = c_runfile.replace('//','/')
        return c_runfile
    else:
        return 'dependency_collection'


# Build run command for popen
# Any arguments and flags must be passed as separate list items
def process_list_gen(z, sig_clear_only, rp_file = None):
    # run_string = '' # No longer used
    run_cmd_list = []
    if z.runfiletype.lower() == 'sas':
        if os.name == 'nt' and binsasscript[-4:].upper() == '.PS1':
            run_cmd_list.append('powershell.exe')
            run_cmd_list.append('-file')
        run_cmd_list.append(binsasscript)
        if binsasscriptparams is not None:
            run_cmd_list = run_cmd_list + binsasscriptparams.split()
        run_cmd_list.append(comp_runfile(z))
        if binsasscriptendparams is not None:
            run_cmd_list = run_cmd_list + binsasscriptendparams.split()
    elif z.runfiletype.lower() == 'shell':
        if os.name == 'nt' and comp_runfile(z)[-4:].upper() == '.PS1':
            run_cmd_list.append('powershell.exe')
            run_cmd_list.append('-file')
        # run_cmd_list = [comp_runfile(z)]
        run_cmd_list.append(comp_runfile(z))
    elif z.runfiletype.lower() == 'schedule':
        if sked_packaged:
            run_cmd_list = [pythoncmd, '-s', comp_runfile(z)]
        else:
            run_cmd_list = [pythoncmd, __file__, '-s', comp_runfile(z)]
        run_cmd_list.append('-n')
        # run_cmd_list.append(logfolder)  # Original functionality pre schedule_tree
        run_cmd_list.append(schedule_tree + '|=|' + logfolder)
        run_cmd_list.append('-a')
        if z.name_alias is not None:
            run_cmd_list.append(full_alias + '/' + z.name_alias)
        else:
            run_cmd_list.append(full_alias + '/' + z.runfile)
        if sig_clear_only:
            run_cmd_list.append('-x')
        if rp_file is not None:
            run_cmd_list.append('-r')
            run_cmd_list.append(rp_file)
        if debug_mode:
            run_cmd_list.append('--debug')
        if notify_all_override:
            run_cmd_list.append('--notifyall')
    if z.shellparam != None:
        run_cmd_list = run_cmd_list + z.shellparam.split()
    # print2(run_cmd_list)
    return run_cmd_list


# Build return code max value acceptance
def max_rc(filetype):
    if filetype.lower() == 'sas':
        return 1  # http://support.sas.com/documentation/cdl/en/hostunx/61879/HTML/default/viewer.htm#retcod.htm
    elif filetype.lower() == 'shell':
        return 0
    elif filetype.lower() == 'schedule':
        return 0
    else:
        return 0

'''
# Validate schedule file exists ( original pre-12/10/2019 logic )
tried_too = 0
if filename == os.path.basename(filename) and not os.path.isfile(filename):
    filename = confpath + filename
    tried_too = 1
if not os.path.isfile(filename):
    if tried_too == 0:
        prselogprint(level='Schedule',
                     level2=None,
                     status='Error',
                     fullrunfile=None,
                     ops_label=None,
                     message='Schedule file ' + filename + ' is not a valid file and path.'
                     )
        print2('error: Schedule file ' + filename + ' is not a valid file and path.')
    if tried_too == 1:
        prselogprint(level='Schedule',
                     level2=None,
                     status='Error',
                     fullrunfile=None,
                     ops_label=None,
                     message='Schedule file ' + os.path.basename(filename) + ' is not a valid file and path. - Also tried: ' + filename
                     )
        print2('error: Schedule file ' + os.path.basename(filename) + ' is not a valid file and path. - Also tried: ' + filename)
    send_email_notify('ERROR: ' + on_machine_email + ' - ' + filenamebase,
                      'Schedule ' + filenamebase + ' does not exist on ' + on_machine_email)
    sys.exit(42)
'''

# Validate schedule file exists
# Check if the parameter given after the -s is an absolute path or relative path
if os.path.isabs(filename):
    # Absolute Path
    if not os.path.isfile(filename):
        # Doesn't exist. Throw Notifications/Errors
        prselogprint(level='Schedule',
                     level2=None,
                     status='Error',
                     fullrunfile=None,
                     ops_label=None,
                     message='Schedule file ' + filename + ' is not a valid file and path.'
                     )
        print2('error: Schedule file ' + filename + ' is not a valid file and path.')
        suppress_further_emails = send_email_notify('ERROR: ' + on_machine_email + ' - ' + filenamebase,
                                                    'Schedule ' + filename + ' does not exist on ' + on_machine_email)
        sys.exit(42)
    else:
        prselogprint(level='Schedule',
                     level2=None,
                     status='Info',
                     fullrunfile=None,
                     ops_label=None,
                     message='Schedule file is running from given location: ' + filename + '.'
                     )
        print2('Info: Schedule file is running from given location: ' + filename + '.')
else:
    # Relative Path - Add confpath from config/env/default in front
    if not os.path.isfile(cwd + '/'+ filename):
        # Doesn't exist in current working directory.
        if not os.path.isfile(confpath + filename):
            # Doesn't exist in the confpath (nor current working directory at this point in nested logic)
            prselogprint(level='Schedule',
                         level2=None,
                         status='Error',
                         fullrunfile=None,
                         ops_label=None,
                         message='Schedule file ' + filename + ' not found in current working directory (' + cwd +
                                 ') nor conf path (' + confpath + ').'
                         )
            print2('error: Schedule file ' + filename + ' not found in current working directory (' + cwd +
                   ') nor conf path (' + confpath + ').')
            suppress_further_emails = send_email_notify('ERROR: ' + on_machine_email + ' - ' + filenamebase,
                                                        'Schedule ' + filename +
                                                        ' does not exist in current working directory (' + cwd +
                                                        ') nor in conf path (' + confpath + ') on ' + on_machine_email)
            sys.exit(42)
        else:
            # Schedule file found in confpath
            prselogprint(level='Schedule',
                         level2=None,
                         status='Info',
                         fullrunfile=None,
                         ops_label=None,
                         message='Schedule file ' + filename + ' is running from ' + confpath + '.'
                         )
            print2('Info: Schedule file ' + filename + ' is running from ' + confpath + '.')
            filename = confpath + filename
    else:
        # Schedule file found in current working directory
        prselogprint(level='Schedule',
                     level2=None,
                     status='Info',
                     fullrunfile=None,
                     ops_label=None,
                     message='Schedule file ' + filename + ' is running from ' + cwd + '.'
                     )
        print2('Info: Schedule file ' + filename + ' is running from ' + cwd + '.')
        filename = cwd + '/' + filename


# Import XML Schedule
Entry = namedtuple('Entry',
                   'runfiletype runfile notify grouping bypassifexists shellparam name_alias email_ini ops_label ' +
                   'depend attempt_rerun long_running_kill')
try:
    tree = ElementTree().parse(filename)
except ParseError as e:
    print2('Schedule XML Parsing error: {err}'.format(err=e))
    prselogprint(level='Schedule',
                 level2=None,
                 status='Error',
                 fullrunfile=None,
                 ops_label=None,
                 message='Schedule XML Parsing error (' + filename + ')'
                 )
    sys.exit(42)

schedule = []
# Initialize precheck_errors here in case any runfile attributes missing on entry
precheck_errors = 0
req_attr_set = 0

# for item in tree.getiterator('entry'):  # Pre-7/26, should still work but going to be deprecated
for item in tree.iter('entry'):
    try:
        runfiletype = item.find('.').get('type')
        runfile = item.find('.').get('file')
        notify = item.find('.').get('notify')
        grouping = item.find('.').get('grouping')  # Placeholder
        bypassifexists = item.find('.').get('bypassifexists')
        shellparam = item.find('.').get('shellparam')
        name_alias = item.find('.').get('name')
        email_ini = item.find('.').get('custom_email_ini')
        ops_label = item.find('.').get('ops_label')
        attempt_rerun = item.find('.').get('attempt_rerun')
        long_running_kill = item.find('.').get('long_running_kill')
        # loopwhileexists = item.find('.').get('loopwhileexists')

        depend = []
        for dependency in item.findall('./depend'):
            dependency_txt = createReplacements(dependency.text.strip(), None)
            depend.append(dependency_txt)

        if notify == 1:
            notify = str(notify)

        if long_running_kill is not None:
            if long_running_kill.upper() != 'Y':
                long_running_kill = None

        if attempt_rerun is not None:
            if isinstance(attempt_rerun, int):
                if attempt_rerun <= 0:
                    attempt_rerun = None
            else:
                try:
                    attempt_rerun = int(attempt_rerun)
                    if attempt_rerun <= 0:
                        attempt_rerun = None
                except:
                    attempt_rerun = None
                    print2('Warning: ' + runfile + ' has invalid, non-integer attempt_rerun set. Will be ignored.')
                    prselogprint(level='Schedule',
                                 level2=None,
                                 status='Warning',
                                 fullrunfile=None,
                                 ops_label=None,
                                 message='Warning: ' + runfile +
                                         ' has invalid, non-integer attempt_rerun set. Will be ignored.'
                                 )

        # Token replacement modifications & first pass error checking on runfile & runfiletype
        if runfiletype is not None:
            runfiletype = runfiletype.strip()
            if runfile is not None:
                if runfiletype.lower() == 'dependency_collection':
                    runfile = 'dependency_collection'
                else:
                    runfile = createReplacements(runfile.strip(), None)
            else:
                if runfiletype.lower() == 'dependency_collection':
                    runfile = 'dependency_collection'
                else:
                    req_attr_set = 1
                    precheck_errors = 1
        else:
            req_attr_set = 1
            precheck_errors = 1
        if email_ini is not None:
            email_ini = createReplacements(email_ini.strip(), None)

        if ops_label is not None:
            ops_label = createReplacements(ops_label.strip(), None)

        if name_alias is not None:
            name_alias = createReplacements(name_alias.strip(), None)

        if shellparam is not None:
            shellparam = createReplacements(shellparam.strip(), None)

        #Note that strip() also occurs on bypass_file byp_i further down in code
        if bypassifexists is not None:
            bypassifexists = createReplacements(bypassifexists.strip(), None)

        # if loopwhileexists is not None:
            # loopwhileexists = createReplacements(loopwhileexists.strip(), None)

        schedule.append(Entry(runfiletype, runfile, notify, grouping, bypassifexists, shellparam,
                              name_alias, email_ini, ops_label, depend, attempt_rerun, long_running_kill))
    except AttributeError as e:
        print2('Element error: {err}'.format(err=e))
        prselogprint(level='Schedule',
                     level2=None,
                     status='Error',
                     fullrunfile=None,
                     ops_label=None,
                     message='Attribute Error reading in schedule (' + filename + ')'
                     )
        sys.exit(42)

# if debug_mode:
#     for x in schedule:
#         stdprint(x)

# print2(schedule)
# print2(schedule[4])

# Required attributes first pass error message
if req_attr_set == 1:
    print2('error: Required attributes (file= and type=) must be set on all schedule entries')
    prselogprint(level='Schedule',
                 level2='Job',
                 status='Error',
                 fullrunfile=None,
                 ops_label=None,
                 message='Required attributes (file= and type=) must be set on all schedule entries'
                 )


# Error checking
# Make sure dependencies align with runfiles
name_alias_re = re.compile(r'^[\w\.\s]+$')
dependencies = []
runfiles = []
none_dependencies = []
bad_dependencies = []
for x in schedule:
    fullfile = comp_runfile(x)
    if fullfile[0:14] == 'error: unknown':
        # print2(fullfile)
        # Moved this error to comp_runfile function
        precheck_errors = 1
    elif not os.path.isfile(fullfile) and fullfile != 'dependency_collection':
        prselogprint(level='Schedule',
                     level2='Job',
                     status='Error',
                     fullrunfile=None,
                     ops_label=None,
                     message=fullfile + ' is not a valid file.'
                     )
        print2('error: {errfile} is not a valid file'.format(errfile=fullfile))
        precheck_errors = 1
    if x.name_alias is not None:
        if name_alias_re.search(x.name_alias) is None:
            prselogprint(level='Schedule',
                         level2='Job',
                         status='Error',
                         fullrunfile=None,
                         ops_label=None,
                         message='name= attribute ' + x.name_alias +
                                 ' must be only letters, numbers, spaces, periods, and underscores.'
                         )
            print2('error: name= attribute ' + x.name_alias +
                   ' must be only letters, numbers, spaces, periods, and underscores.')
            precheck_errors = 1
        elif x.name_alias.upper() == 'NONE':
            prselogprint(level='Schedule',
                         level2='Job',
                         status='Error',
                         fullrunfile=None,
                         ops_label=None,
                         message='name= attribute may not be called "NONE".'
                         )
            print2('error: name= attribute may not be called "NONE".')
            precheck_errors = 1
        if x.name_alias in runfiles:
            print2('error: name= attribute ' + x.name_alias +
                   ' already exists in schedule or overlaps with file= in another entry. Must be unique.')
            precheck_errors = 1
            prselogprint(level='Schedule',
                         level2='Job',
                         status='Error',
                         fullrunfile=None,
                         ops_label=None,
                         message='name= attribute ' + x.name_alias +
                                 ' already exists in schedule or overlaps with file= in another entry. Must be unique.'
                         )
        if x.name_alias in full_alias_split and x.runfiletype.lower() == 'schedule':
            print2('error: name= attribute ' + x.name_alias +
                   ' overlaps with a parent schedule name_alias for this schedule')
            precheck_errors = 1
            prselogprint(level='Schedule',
                         level2='Job',
                         status='Error',
                         fullrunfile=None,
                         ops_label=None,
                         message='name= attribute ' + x.name_alias +
                                 ' overlaps with a parent schedule name_alias for this schedule'
                         )

        runfiles.append(x.name_alias)
    else:
        if '/' in x.runfile or '\\' in x.runfile:
            print2('error: name= attribute must be set for files with full or relative path declared. (' + x.runfile +
                   ')')
            prselogprint(level='Schedule',
                         level2='Job',
                         status='Error',
                         fullrunfile=None,
                         ops_label=None,
                         message='name= attribute must be set for files with full or relative path declared'
                         )
            precheck_errors = 1
        elif x.runfiletype.lower() == 'dependency_collection':
            print2('error: name= attribute must be set for type dependency_collection')
            prselogprint(level='Schedule',
                         level2='Job',
                         status='Error',
                         fullrunfile=None,
                         ops_label=None,
                         message='name= attribute must be set for type dependency_collection'
                         )
            precheck_errors = 1
        else:
            if x.runfile in runfiles:
                print2('error: file= attribute ' + x.runfile +
                       ' already exists in schedule or overlaps with name= in another entry. Must be unique.')
                prselogprint(level='Schedule',
                             level2='Job',
                             status='Error',
                             fullrunfile=None,
                             ops_label=None,
                             message='file= attribute ' + x.runfile + ' already exists in schedule ' +
                                     'or overlaps with name= in another entry. Must be unique.'
                             )
                precheck_errors = 1
            runfiles.append(x.runfile)
    if len(x.depend) == 0:
        print2('error: entry with file= ' + x.runfile + ' has no dependencies. Must at least one dependency. ' +
               '(may be "NONE")')
        prselogprint(level='Schedule',
                     level2='Job',
                     status='Error',
                     fullrunfile=None,
                     ops_label=None,
                     message='entry with file= ' + x.runfile + ' has no dependencies. Must at least one dependency. ' +
                             '(may be "NONE")'
                     )
        precheck_errors = 1
    for j in x.depend:
        if j.upper() != 'NONE':
            if '/' not in j and '\\' not in j:
                dependencies.append(j)
            else:
                bad_dependencies.append(j)
        else:
            none_dependencies.append(j)

# Check to make sure no full paths are in dependencies
if len(bad_dependencies) != 0:
    print2('error: Full paths or relative paths with filenames aren\'t ' +
           'allowed in dependencies. Use name= attribute on entry and for dependency')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Error',
                 fullrunfile=None,
                 ops_label=None,
                 message='Full paths or relative paths with filenames aren\'t ' +
                         'allowed in dependencies. Use name= attribute on entry and for dependency'
                 )
    precheck_errors = 1

# Check that at least one program/job has no dependencies as a starting point
if len(none_dependencies) == 0:
    print2('error: At least one job in schedule needs to have no dependencies')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Error',
                 fullrunfile=None,
                 ops_label=None,
                 message='At least one job in schedule needs to have no dependencies'
                 )
    precheck_errors = 1

# Check that dependencies are a subset of runfiles
if not set(dependencies).issubset(runfiles):
    print2('error: Not all dependencies found as entries in schedule. Check case sensitivity')
    print2(set(dependencies).difference(runfiles))
    prselogprint(level='Schedule',
                 level2=None,
                 status='Error',
                 fullrunfile=None,
                 ops_label=None,
                 message='Not all dependencies found as entries in schedule. Check case sensitivity'
                 )
    precheck_errors = 1

# Check that no dependency loops exist in schedule that will never be entered
check_schedule = schedule
check_jobs_fulllist = []
check_jobs_complete = []
iterations = 0
while len(check_schedule) > len(check_jobs_complete) and iterations <= len(schedule):
    for item in check_schedule:
        alias_job = sch_st_key(item)
        if alias_job not in check_jobs_fulllist:
            check_jobs_fulllist.append(alias_job)
        if alias_job not in set(check_jobs_complete) and \
                (set(item.depend).issubset(check_jobs_complete) or item.depend[0].upper() == 'NONE'):
            check_jobs_complete.append(alias_job)
    iterations += 1
if len(check_schedule) != len(check_jobs_complete):
    check_jobs_unable_to_run = [ item for item in check_jobs_fulllist if item not in check_jobs_complete ]
    print2('error: Schedule cannot complete as specified. ' +
           'Check for dependencies that will never be met due to dependency loops. Check jobs listed in array below.')
    print2(check_jobs_unable_to_run)
    prselogprint(level='Schedule',
                 level2=None,
                 status='Error',
                 fullrunfile=None,
                 ops_label=None,
                 message='Schedule cannot complete as specified. Check for dependencies that ' +
                         'will never be met due to dependency loops'
                 )
    precheck_errors = 1

# testing
# from pprint import pprint
# pprint(check_schedule)
# sys.exit(42)

# If any of above error conditions present.
if precheck_errors == 1:
    sys.exit(42)
if test_schedule_only is True:
    print2('Finished: Testing Schedule Completed Successfully (-t flag set).')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Finished',
                 fullrunfile=filename,
                 ops_label=None,
                 message='Testing Schedule Completed Successfully (-t flag set).'
                 )
    sys.exit(0)

# Place schedule started/restarted signal
clear_signals_for_regular_run = False
# Used to delay signal clear code for later to make sure start signal isn't cleared before filelock/test
clear_sig_before_run = 0

# stdprint(notify_start)
# stdprint(exist_signal(filenamebase + '-started.sig'))
# stdprint(exist_signal(filenamebase + '-finished.sig'))
# stdprint(signal_clear_only)
# stdprint(force_full_restart)
# stdprint(type(notify_start))

# Status Report Code for a running Schedule
if report_file is not None:
    print2('Info: Report being generated (-r flag set -- value: ' + report_file + ').')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Info',
                 fullrunfile=filename,
                 ops_label=None,
                 message='Report being generated (-r flag set -- value: ' + report_file + ').'
                 )

    valid_report_file = 0
    if report_file == 'STDOUT':
        valid_report_file = 1
        if not nested_instance:
            print('schedule|job|status|started|finished|dependencies')
    else:
        report_file_path = rreplace(os.path.realpath(report_file),
                                    os.path.basename(report_file), '', 1).replace('\\', '/')
        # stdprint(report_file_path)
        if os.path.isabs(report_file):
            if os.path.exists(report_file_path):
                valid_report_file = 1
                if not nested_instance:
                    with open(report_file, 'w') as w:
                        w.write('schedule|job|status|started|finished|dependencies\n')
            else:
                print2("Error: Report file path doesn't exist. ( " + report_file_path + ').')
                prselogprint(level='Schedule',
                             level2=None,
                             status='Error',
                             fullrunfile=filename,
                             ops_label=None,
                             message="Report file path doesn't exist. ( " + report_file_path + ').'
                             )
        else:
            report_file = os.path.join(cwd, report_file)
            report_file_path = rreplace(os.path.realpath(report_file),
                                        os.path.basename(report_file), '', 1).replace('\\', '/')
            if os.path.exists(report_file_path):
                valid_report_file = 1
                if not nested_instance:
                    with open(report_file, 'w') as w:
                        w.write('schedule|job|status|started|finished|dependencies\n')
            else:
                print2("Error: Report file path doesn't exist. ( " + report_file_path + ').')
                prselogprint(level='Schedule',
                             level2=None,
                             status='Error',
                             fullrunfile=filename,
                             ops_label=None,
                             message="Report file path doesn't exist. ( " + report_file_path + ').'
                             )
    if valid_report_file == 1:
        to_report = 0
        if exist_signal(filenamebase + '-ERROR.sig') and not exist_signal(filenamebase + '-finished.sig'):
            # started and hasn't finished successfully
            with open(sigpath + filenamebase + '-started.sig', 'r') as st:
                with open(sigpath + filenamebase + '-ERROR.sig', 'r') as er:
                    line = filenamebase + '|_SCHEDULELEVEL_|ERROR|' + st.read().split('\n')[-2].split('|')[0] + '|' +\
                           er.read().split('\n')[-2].split('|')[0] + '|'
            if report_file == 'STDOUT':
                print(line)
            else:
                with open(report_file, 'a') as w:
                    w.write(line + '\n')
            to_report = 1
        elif exist_signal(filenamebase + '-started.sig') and not exist_signal(filenamebase + '-finished.sig'):
            # started and hasn't finished successfully
            with open(sigpath + filenamebase + '-started.sig', 'r') as st:
                line = filenamebase + '|_SCHEDULELEVEL_|Started|' + st.read().split('\n')[-2].split('|')[0] + '||'
            if report_file == 'STDOUT':
                print(line)
            else:
                with open(report_file, 'a') as w:
                    w.write(line + '\n')
            to_report = 1
        elif exist_signal(filenamebase + '-started.sig') and exist_signal(filenamebase + '-finished.sig'):
            with open(sigpath + filenamebase + '-started.sig', 'r') as st:
                with open(sigpath + filenamebase + '-finished.sig', 'r') as fn:
                    line = filenamebase + '|_SCHEDULELEVEL_|Finished|' + st.read().split('\n')[-2].split('|')[0] + '|' \
                           + fn.read().split('\n')[-2].split('|')[0] + '|'
                    if report_file == 'STDOUT':
                        print(line)
                    else:
                        with open(report_file, 'a') as w:
                            w.write(line + '\n')
            to_report = 1
        elif not exist_signal(filenamebase + '-started.sig') and not exist_signal(filenamebase + '-finished.sig'):
            # no signals present (cleared previously or initial run)
            line = filenamebase + '|_SCHEDULELEVEL_|Not_Started|||'
            if report_file == 'STDOUT':
                print(line)
            else:
                with open(report_file, 'a') as w:
                    w.write(line + '\n')
            to_report = 1
        if to_report == 1:
            for x in schedule:
                start_signal = sigpath + filenamebase + '_' + sch_st_key(x) + '-started.sig'
                finish_signal = sigpath + filenamebase + '_' + sch_st_key(x) + '-finished.sig'
                bypass_signal = sigpath + filenamebase + '_' + sch_st_key(x) + '-bypassed.sig'
                error_signal = sigpath + filenamebase + '_' + sch_st_key(x) + '-ERROR.sig'

                dpds = ','.join(x.depend)

                if exist_signal_job(x, 'bypassed'):
                    with open(bypass_signal, 'r') as by:
                        line = filenamebase + '|' + sch_st_key(x) + '|Bypassed|' + \
                               by.read().split('\n')[-2].split('|')[0] + '||' + dpds
                elif exist_signal_job(x, 'finished') and exist_signal_job(x, 'started'):
                    with open(start_signal, 'r') as st:
                        with open(finish_signal, 'r') as fn:
                            line = filenamebase + '|' + sch_st_key(x) + '|Finished|' + \
                                   st.read().split('\n')[-2].split('|')[0] + '|' + \
                                   fn.read().split('\n')[-2].split('|')[0] + '|' + dpds
                elif exist_signal_job(x, 'started'):
                    if exist_signal_job(x, 'ERROR'):
                        with open(start_signal, 'r') as st:
                            with open(error_signal, 'r') as er:
                                line = filenamebase + '|' + sch_st_key(x) + '|ERROR|' + \
                                       st.read().split('\n')[-2].split('|')[0] + '|' + \
                                       er.read().split('\n')[-2].split('|')[0] + '|' + dpds
                    else:
                        # Running
                        with open(start_signal, 'r') as st:
                            line = filenamebase + '|' + sch_st_key(x) + '|Running|' + \
                                   st.read().split('\n')[-2].split('|')[0] + '||' + dpds
                else:
                    # Not started yet
                    line = filenamebase + '|' + sch_st_key(x) + '|Not_Started|||' + dpds
                if report_file == 'STDOUT':
                    print(line)
                else:
                    with open(report_file, 'a') as w:
                        w.write(line+'\n')
                if x.runfiletype == 'schedule':
                    # stdprint('hhhhhhhhhhhhhhhhhhhhhh')
                    process_for_report = Popen(process_list_gen(x, False, rp_file=report_file), stdout=PIPE, env=osenv)
                    process_for_report.wait()
                    if report_file == 'STDOUT':
                        rp_stdout = process_for_report.stdout.read().decode('utf-8')
                        rp_stdout = rp_stdout.split('\n')
                        rp_stdout = '\n'.join(rp_stdout[0:len(rp_stdout)-1])
                        print(rp_stdout)
                    if process_for_report.returncode > 0:
                        print2('error: Sub-schedule ' + os.path.basename(x.runfile) +
                               ' failure during report (-r <STDOUT|report_file>)')
                        prselogprint(level='Schedule',
                                     level2=None,
                                     status='Error',
                                     fullrunfile=filename,
                                     ops_label=None,
                                     message='Sub-schedule ' + os.path.basename(x.runfile) +
                                             ' failure during report (-r <STDOUT|report_file>)'
                                     )
                        sys.exit(42)

    else:
        sys.exit(42)

    print2('Info: Report finished (-r flag set -- value: ' + report_file + ').')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Info',
                 fullrunfile=filename,
                 ops_label=None,
                 message='Report finished (-r flag set -- value: ' + report_file + ').'
                 )
    sys.exit(0)
'''
def signal_wrapper(jentry, jstatus, jfunction, return_code='n'):
    signal_name = filenamebase + '_' + sch_st_key(jentry)
    signal_name = signal_name + '-' + jstatus + '.sig'
    if return_code != 'y':
        jfunction(signal_name)
    else:
        return jfunction(signal_name)

def exist_signal(sname):
    if os.path.isfile(sigpath + sname):
        return True
    else:
        return False

def exist_signal_job(jentry, jstatus):
    return signal_wrapper(jentry, jstatus, exist_signal, return_code='y')
'''

if exist_signal(filenamebase + '-started.sig'):
    start_sig_exist = 1
else:
    start_sig_exist = 0
place_signal(filenamebase + '-started.sig', write_in='n')
# First time run
if signal_clear_only is False \
        and start_sig_exist == 0 \
        and exist_signal(filenamebase + '-finished.sig') is False:
    if notify_start == 1 or notify_all_override:
        suppress_further_emails = send_email_notify('STARTED: ' + on_machine_email + ' - ' + filenamebase,
                                                    'Schedule ' + filenamebase + ' started on ' + on_machine_email)
# Restarted run
elif start_sig_exist == 1 \
        and exist_signal(filenamebase + '-finished.sig') is False \
        and signal_clear_only is False \
        and force_full_restart is False:
    place_signal(filenamebase + '-restarted.sig', write_in='n')
    exist_del_signal(filenamebase + '-stopped_gracefully.sig')
    # stdprint('we get here first')
    if notify_start == 1 or notify_all_override:
        # stdprint('we get here')
        suppress_further_emails = send_email_notify('RESTARTED: ' + on_machine_email + ' - ' + filenamebase,
                                                    'Schedule ' + filenamebase + ' started on ' + on_machine_email)
# Force full restart or previous run completed successfully
else:
    # This code moved below the file lock check.
    clear_sig_before_run = 1

if plugin_to_load is not None and hasattr(sked_plugin, 'on_schedule_start') and signal_clear_only is False:
    sked_plugin.on_schedule_start(filename, check_schedule, config_file)

# Add lock to start signal. If schedule exits gracefully it will automatically be released. If schedule doesn't end
# gracefully (e.g: kill -9) then it will also be released. Ops will use this as a true sign of whether or not sked
# is still running. Note this is only for linux environments.
# '''

try:
    import fcntl
    started_signal_lock = open(sigpath + filenamebase + '-started.sig', 'w')  # certain file systems require 'w'
    fcntl.flock(started_signal_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # can use 'r' but some file systems need 'w'
    # fcntl.lockf(started_signal_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # requires file opened with 'w' instead of 'r'
    # fcntl.lockf(x, fcntl.LOCK_EX)
    lock_obtained = 1

except:  # TypeError as e:
    # stdprint("Unexpected error:", sys.exc_info()[0])
    # stdprint(e)
    lock_obtained = 0
    if os.name == 'nt':
        prselogprint(level='Schedule',
                     level2=None,
                     status='Info',
                     fullrunfile=None,
                     ops_label=None,
                     message='File lock on start signal not obtained. (Only works on Linux)'
                     )
        print2('Info: File lock on start signal not obtained. (Only works on Linux)')
    else:
        prselogprint(level='Schedule',
                     level2=None,
                     status='Error',
                     fullrunfile=None,
                     ops_label=None,
                     message='Schedule Already Running. File lock found. (' + filenamebase + '-started.sig' + ')'
                     )
        print2('Error: Schedule Already Running. File lock found. (' + filenamebase + '-started.sig' + ')')
        suppress_further_emails = send_email_notify('ERROR: ' + on_machine_email + ' - ' + filenamebase,
                                                    'Schedule ' + filenamebase + ' already running on ' +
                                                    on_machine_email)
        sys.exit(42)
# '''

# This is the code for the else block above that's moved to after the filelock has been checked. We don't want to
# clear the signals out before testing a filelock to see if another sked instance is currently running the same
# schedule.
# Force full restart or previous run completed successfully
if clear_sig_before_run == 1:
    # exist_del_signal(filenamebase + '-started.sig')
    exist_del_signal(filenamebase + '-restarted.sig')
    exist_del_signal(filenamebase + '-finished.sig')
    exist_del_signal(filenamebase + '-bypassed.sig')
    exist_del_signal(filenamebase + '-stopped_gracefully.sig')
    if signal_clear_only is False:
        clear_signals_for_regular_run = True
        if notify_start == 1 or notify_all_override:
            if force_full_restart is True:
                suppress_further_emails = send_email_notify('STARTED: ' + on_machine_email + ' - ' + filenamebase,
                                                            'Schedule ' + filenamebase +
                                                            ' started on ' + on_machine_email + ' with -f')
            else:
                suppress_further_emails = send_email_notify('STARTED: ' + on_machine_email + ' - ' + filenamebase,
                                                            'Schedule ' + filenamebase +
                                                            ' started on ' + on_machine_email)

# Earlier started signal created if it didn't exist. This step adds contents to it. Create first, flock check 2nd,
# add contents last. If signal clear only run then remove the signal if it exists due to flock check.
if signal_clear_only is False:
    place_signal(filenamebase + '-started.sig')
else:
    if lock_obtained == 1:
        fcntl.flock(started_signal_lock, fcntl.LOCK_UN)
    exist_del_signal(filenamebase + '-started.sig')
exist_del_signal(filenamebase + '-ERROR.sig')

# Schedule Pre-Work
# Setup list to keep track of process name and whether it's running or not
# Runfile, running, completed, placeholder for polling process, placeholder for results
schedule_status = dict()
schedule_status_popen = []  # List to hold popens since dictionary values cannot be mutable types
popen_counter = 0  # Set up the reference position of the popen list in the dictionary
for x in schedule:
    schedule_status_key = sch_st_key(x)  # runfile or alias
    # key
    # v[0]=running flg
    # v[1]=completed flg
    # v[2]=position in schedule_status_popen for popen of job
    # v[3]=rc from job when finished, None otherwise
    # v[4]=datetime.datetime.now() from job start
    # v[5]=runfiletype from schedule obj
    # v[6]=job bypassed flg
    # v[7]=max rc still considered success - only set on job_start()
    # v[8]=placeholder for popen stdout
    schedule_status[schedule_status_key] = [0, 0, popen_counter, None, None, None, 0, None, None]
    schedule_status_popen.append(None)
    popen_counter += 1
# print2(schedule_status)
# print2(schedule_status['batch_dailycycle_init.sas'][3])
# sys.exit(123)


# Function to stop the schedule in it's tracks and close everything open immediately.
def terminate_all_jobs():
    for k, v in schedule_status.items():
        if v[0] == 1 and v[5] == 'schedule':  # k[-4:]=='.xml':
            for x in schedule:
                if sch_st_key(x) == k:
                    place_signal(x.runfile + '_STOPKILL.txt')
            # stdprint('place stopkill for: '+k)
        elif v[0] == 1 and v[5] != 'dependency_collection':
            if os.name == 'posix':
                # temppid = schedule_status_popen[schedule_status[k][2]].pid
                os.killpg(os.getpgid(schedule_status_popen[schedule_status[k][2]].pid), signal.SIGKILL)
            else:
                schedule_status_popen[schedule_status[k][2]].terminate()
    return send_email_notify('USER TERMINATED: ' + on_machine_email + ' - ' + filenamebase, 'Schedule ' + filenamebase +
                             ' terminated by signal on ' + on_machine_email)


class ThreadedPipeReader(threading.Thread):
    """
    Utility class used to continuously read from a process.PIPE in order to
    prevent blocked processes from hanging when they fill up the PIPE's buffer
    """

    def __init__(self, pipe, queue):
        assert isinstance(queue, Queue)
        assert callable(pipe.readline)
        threading.Thread.__init__(self)
        self._pipe = pipe
        self._queue = queue

    def run(self):
        while True:
            _line = self._pipe.readline()

            if _line:
                self._queue.put(_line.decode('utf-8'))
            else:
                break

        self._queue.put(None)  # Put a None value to represent end of queue
        self._pipe.close()


# Function called upon job start
def job_start(jentry, sig_clear_only):
    # print(suppress_further_emails)
    erc = suppress_further_emails
    # print(erc)
    schedule_status_key = sch_st_key(jentry)
    schedule_status[schedule_status_key][4] = datetime.datetime.now()  # Grab start time for duration and logs
    schedule_status[schedule_status_key][5] = jentry.runfiletype.lower()
    if sig_clear_only is False:
        remove_from_schedule.append(jentry)  # Add for cleanup later from schedule
        # Job has run already - this is a restarted run
        if exist_signal_job(jentry, 'finished') and \
                not exist_signal(filenamebase + '_' + schedule_status_key + '_LOOP.txt'):
            schedule_status[schedule_status_key][1] = 1  # Mark job complete
            jobs_run.append(schedule_status_key)  # Append job to jobs_run for dependency checking
        else:  # Job needs to run because it hasn't previously completed
            schedule_status[schedule_status_key][7] = max_rc(jentry.runfiletype)  # max_rc for success stored w/status
            schedule_status[schedule_status_key][0] = 1  # Mark job running
            if exist_signal_job(jentry, 'started'):  # If started signal exists, place restart signal
                place_signal_job(jentry, 'started')
                place_signal_job(jentry, 'restarted')
                existrem_signal_job(jentry, 'ERROR')
                print2(schedule_status[schedule_status_key][4].strftime("%Y-%m-%d %H:%M:%S - ") +
                       'Restarting: ' + schedule_status_key)
                prselogprint(level='Job',
                             level2=None,
                             status='Restarting',
                             fullrunfile=comp_runfile(jentry),
                             name_alias=jentry.name_alias,
                             ops_label=jentry.ops_label,
                             message=None
                             )
            else:
                place_signal_job(jentry, 'started')  # If started signal does not exist, place start signal
                print2(schedule_status[schedule_status_key][4].strftime("%Y-%m-%d %H:%M:%S - ") +
                       'Starting: ' + schedule_status_key)
                prselogprint(level='Job',
                             level2=None,
                             status='Starting',
                             fullrunfile=comp_runfile(jentry),
                             name_alias=jentry.name_alias,
                             ops_label=jentry.ops_label,
                             message=None
                             )

            # Actually start the job and hold the popen in the appropriate place in the popen list
            # start_new_session=True is needed along with terminate_all_jobs() killpg to prevent main sked session
            # from going when killing the process groups. It causes a new process group in linux to be started with
            # each schedule entry.
            if jentry.runfiletype.lower() == 'dependency_collection':
                schedule_status[schedule_status_key][3] = 0 # set rc to 0 so  it's automatically successful
            else:
                schedule_status_popen[schedule_status[schedule_status_key][2]] = \
                    Popen(process_list_gen(jentry, sig_clear_only), stdout=PIPE, start_new_session=True, env=osenv)

                _stdout_queue = Queue()
                _stdout_reader = ThreadedPipeReader(schedule_status_popen[schedule_status[schedule_status_key][2]].stdout, _stdout_queue)
                _stdout_reader.start()

                schedule_status[schedule_status_key][8] = (_stdout_reader, _stdout_queue)

            # Run plugin function on_job_start
            if plugin_to_load is not None and hasattr(sked_plugin, 'on_job_start'):
                sked_plugin.on_job_start(filename, check_schedule, jentry, schedule_status, config_file)

            # If schedule xml entry has notify set to 1 send an email
            if (jentry.notify is not None and jentry.notify == '1') or notify_all_override:
                # print(erc)
                if exist_signal(filenamebase + '_' + schedule_status_key + '_LOOP.txt'):
                    erc = send_email_notify('STARTED (LOOP): ' + on_machine_email + ' - ' + filenamebase + ' - ' +
                                            schedule_status_key,
                                            'Machine: ' + on_machine_email + '\n' +
                                            'Schedule: ' + filenamebase + '\n' +
                                            'Job Started: ' + schedule_status_key)
                else:
                    erc = send_email_notify('STARTED: ' + on_machine_email + ' - ' + filenamebase + ' - ' +
                                            schedule_status_key,
                                            'Machine: ' + on_machine_email + '\n' +
                                            'Schedule: ' + filenamebase + '\n' +
                                            'Job Started: ' + schedule_status_key)
                # print(erc)
            if erc == 0:
                erc = send_email_notify_custom(jentry, 'Started')
                # print(erc)
    else:  # sig_clear_only == True
        existrem_signal_job(jentry, 'started')
        existrem_signal_job(jentry, 'restarted')
        existrem_signal_job(jentry, 'finished')
        # existrem_signal_job(jentry, 'finishedprev')
        existrem_signal_job(jentry, 'bypassed')
        existrem_signal_job(jentry, 'ERROR')
        if jentry.runfiletype == 'schedule':  # Call sub-schedule w/-x option (clearsignals)
            print2(schedule_status[schedule_status_key][4].strftime(
                "%Y-%m-%d %H:%M:%S - ") + 'Start_ClearSignals: ' + schedule_status_key)
            prselogprint(level='Job',
                         level2=None,
                         status='Start_ClearSignals',
                         fullrunfile=comp_runfile(jentry),
                         name_alias=jentry.name_alias,
                         ops_label=jentry.ops_label,
                         message=None
                         )
            process_for_clear = Popen(process_list_gen(jentry, sig_clear_only), stdout=DEVNULL, env=osenv)
            ''' # Old logic wasn't capturing the sub-schedule validation error correctly. Added lines below for
                # process_for_clear.wait() and to check returncode and fail if needed.
            while True:  # wait for popen to finish, then break
                lineresult = process_for_clear.stdout.readline().decode()
                if not lineresult:
                    break
            '''
            process_for_clear.wait()
            if process_for_clear.returncode > 0:
                print2('error: Sub-schedule ' + os.path.basename(jentry.runfile) +
                       ' failure during signal clear and validation. Check sub-schedule logs. ' +
                       'Once sub-schedule is fixed restart main schedule with -f to resolve issue')
                prselogprint(level='Schedule',
                             level2=None,
                             status='Error',
                             fullrunfile=filename,
                             ops_label=None,
                             message='Sub-schedule ' + os.path.basename(jentry.runfile) +
                                     ' failure during signal clear and validation. Check sub-schedule logs. ' +
                                     'Once sub-schedule is fixed restart main schedule with -f to resolve issue'
                             )
                sys.exit(42)
                # stdprint(lineresult)
        else:  # not a schedule file
            print2(
                schedule_status[schedule_status_key][4].strftime("%Y-%m-%d %H:%M:%S - ") +
                'ClearSignals: ' + schedule_status_key)
            prselogprint(level='Job',
                         level2=None,
                         status='ClearSignals',
                         fullrunfile=comp_runfile(jentry),
                         name_alias=jentry.name_alias,
                         ops_label=jentry.ops_label,
                         message=None
                         )
    return erc

# Clear signals on clear signals only parameter or force full restart
if signal_clear_only or force_full_restart or clear_signals_for_regular_run:
    for x in schedule:
        suppress_further_emails = job_start(x, True)  # Call job_start w/sig_clear_only as True


# A function to complete jobs successfully that won't actually run (bypass or previously run)
def complete_no_run(jentry,why_complete):
    erc = suppress_further_emails
    remove_from_schedule.append(jentry)
    schedule_status_key = sch_st_key(jentry)
    # schedule_status[x.runfile][0] = 1
    schedule_status[schedule_status_key][3] = -1
    # stdprint('previously completed: '+x.runfile)
    if why_complete == 'finishprev':
        erc = send_email_notify_custom(jentry, 'FinishedPrev')
        if (jentry.notify == '1' or notify_all_override) and erc == 0:
            erc = send_email_notify(
                    'FINISHED PREVIOUSLY: ' + on_machine_email + ' - ' + filenamebase + ' - ' + schedule_status_key,
                    'Machine: ' + on_machine_email + '\n' +
                    'Schedule: ' + filenamebase + '\n' +
                    'Finished Previously: ' + schedule_status_key)
        if plugin_to_load is not None and hasattr(sked_plugin, 'on_job_finishedprev'):
            sked_plugin.on_job_finishedprev(filename, check_schedule, jentry, schedule_status, config_file)
    elif why_complete == 'bypass':
        erc = send_email_notify_custom(jentry, 'Bypassed')
        if (jentry.notify == '1' or notify_all_override) and erc == 0:
            erc = send_email_notify('BYPASSED: ' + on_machine_email + ' - ' + filenamebase + ' - ' + schedule_status_key,
                              'Machine: ' + on_machine_email + '\n' +
                              'Schedule: ' + filenamebase + '\n' +
                              'Job Bypassed: ' + schedule_status_key)
        if plugin_to_load is not None and hasattr(sked_plugin, 'on_job_bypassed'):
            sked_plugin.on_job_bypassed(filename, check_schedule, jentry, schedule_status, config_file)
    return erc


def schedule_end_w_errors():
    print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Exit: Errors Present')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Error',
                 fullrunfile=filename,
                 ops_label=None,
                 message='Errors present in schedule. Exiting.'
                 )
    if cfg_scheduletype_errors == 'Y' or notify_all_override:
        erc = send_email_notify('ERRORS PRESENT: ' + on_machine_email + ' - ' + filenamebase,
                                'Schedule ' + filenamebase + ' exited due to errors ' + on_machine_email)
    place_signal(filenamebase + '-ERROR.sig')
    if plugin_to_load is not None and hasattr(sked_plugin, 'on_schedule_error_stop') and signal_clear_only is False:
        sked_plugin.on_schedule_error_stop(filename, check_schedule, config_file)
    sys.exit(42)

# stdprint(schedule[4])


# if number of entries in schedule matches number of entries in previous durations file then sort schedule by
#  descending duration remaining (based upon dependencies and flow). else if avg_past_duration > 0  then previous
# file available but not an entry available for every schedule

# pair_timing defaults to 0 durations that are unavailable
def pair_timing(x):
    if debug_mode and report_file is None:
        stdprint('pair_timing() for ' + x)
    try:
        value = avg_past_duration[x]
    except:
        value = 0
        if debug_mode and report_file is None:
            stdprint('pair_timing() for ' + x + ' set to 0')
    return value


if debug_mode and report_file is None:
    for x in schedule:
        stdprint(x)


# used to crawl from the end of a schedule to the beginning while adding past durations to get time remaining
def recurseForward(x, recurseTime):
    if debug_mode and report_file is None:
        stdprint(x)
        stdprint(recurseTime)
    if x.depend[0].upper() != 'NONE':
        for dep in x.depend:
            for s in schedule:
                if sch_st_key(s) == dep:
                    if debug_mode and report_file is None:
                        stdprint(dep)
                        stdprint('s')
                        stdprint(s)
                    tempTime = pair_timing(dep) + recurseTime
                    if debug_mode and report_file is None:
                        stdprint(tempTime)
                        stdprint(time_remaining[dep])
                    if time_remaining[dep] < tempTime:
                        time_remaining[dep] = tempTime
                    if debug_mode and report_file is None:
                        stdprint(time_remaining[dep])
                    recurseForward(s, time_remaining[dep])

# stdprint(schedule)

# if conditions below are met then bias schedule kick-off order based upon time remaining
if max_concurrent_jobs < 999 and optimize_concurrency is not None and optimize_concurrency == 1 and \
                signal_clear_only is False:
    if len(avg_past_duration) >= len(schedule)*.75:  # arbitrarily chose .75 to indicate that if durations available for
                                                    # 75% or more of the jobs in the schedule then optimize. Note that
                                                    # job durations could be extraneous from past runs that have since
                                                    # been removed from the overall schedule.

        # stdprint(dependencies)
        # stdprint(runfiles)

        # find jobs that no other jobs are dependent on -- "end of chain" jobs
        end_of_chain = []
        for x in runfiles:
            if x not in dependencies:
                end_of_chain.append(x)
        if debug_mode and report_file is None:
            stdprint('end_of_chain')
            stdprint(end_of_chain)
        # stdprint(end_of_chain)

        # initialize time remaining values to 0
        time_remaining = {}
        for x in schedule:
            time_remaining[sch_st_key(x)] = 0
        if debug_mode and report_file is None:
            stdprint('time_remaining')
            stdprint(time_remaining)

        # start at the end of the schedule and call the recurseForward function to build time remaining durations
        for x in schedule:
            if sch_st_key(x) in end_of_chain:
                time_remaining[sch_st_key(x)] = pair_timing(sch_st_key(x))
                recurseForward(x, time_remaining[sch_st_key(x)])

        # stdprint(avg_past_duration)
        # stdprint(time_remaining)

        # sort schedule by time remaining values descending in order to bias jobs kicked off
        schedule.sort(key=lambda Entry: time_remaining[sch_st_key(Entry)], reverse=True)

        # stdprint(schedule)
        # stdprint(time_remaining)
        # to_print_out = []
        # for x in schedule:
        #     to_print_out.append(x.runfile)
        # stdprint(to_print_out)
    elif len(avg_past_duration) > 0:
        print2(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
            'Info: Previous job duration present but not enough entries for every schedule entry (>75%)')
        prselogprint(level='Schedule',
                     level2=None,
                     status='Info',
                     fullrunfile=filename,
                     ops_label=None,
                     message='Previous job duration file present but not enough entries for every schedule entry (>75%)'
                     )
else:
    print2(
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
        'Info: Previous job duration present but max_concurrent_jobs is 999 or optimize_concurrency ne 1')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Info',
                 fullrunfile=filename,
                 ops_label=None,
                 message='Previous job duration present but max_concurrent_jobs is 999 or optimize_concurrency ne 1'
                 )
# sys.exit("STOP: line 1625+ testing... do not run actual schedule")

# Run Schedule
errors_present = False
temp_stop = 0
jobs_cur_running = 0
total_time = 0
long_running_alert = []
attempted_rerun = {}
if not signal_clear_only:  # Important for when sked called with -x option
    while len(schedule) != 0 or stop_gracefully:
        # Loop to check status of jobs and dependencies - kick off jobs if able
        remove_from_schedule = []
        jobs_kicked_off = 0

        # Check for job restart signals from user having fixed an error that occurred during run.
        rem_fr_errd_jobs = []
        len_prev_errd_jobs = len(errored_jobs)
        if len_prev_errd_jobs > 0:
            '''
            for k in errored_jobs:
                if exist_signal(filenamebase + '_' + k + '_RESTART.txt'):
                    remove_signal(filenamebase + '_' + k + '_RESTART.txt')
                    schedule_status[k][0] = 0
                    schedule_status[k][1] = 0
                    rem_fr_errd_jobs.append(k)

                    print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
                               'Restart Signal Found: ' + k)

                    for x in schedule:
                        if k == sch_st_key(x):
                            prselogprint(level='Job',
                                         level2=None,
                                         status='RestartSig',
                                         fullrunfile=comp_runfile(x),
                                         name_alias=x.name_alias,
                                         ops_label=x.ops_label,
                                         message=None
                                        )
            '''
            for k in errored_jobs:
                for x in schedule:
                    if k == sch_st_key(x):
                        if exist_signal(filenamebase + '_' + k + '_RESTART.txt'):
                            remove_signal(filenamebase + '_' + k + '_RESTART.txt')
                            schedule_status[k][0] = 0
                            schedule_status[k][1] = 0
                            schedule_status[k][3] = None
                            rem_fr_errd_jobs.append(k)

                            print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
                                   'Restart Signal Found: ' + k)
                            prselogprint(level='Job',
                                         level2=None,
                                         status='RestartSig',
                                         fullrunfile=comp_runfile(x),
                                         name_alias=x.name_alias,
                                         ops_label=x.ops_label,
                                         message=None
                                         )

                        if x.attempt_rerun is not None and \
                                (k not in attempted_rerun.keys() or attempted_rerun[k] < x.attempt_rerun):
                            schedule_status[k][0] = 0
                            schedule_status[k][1] = 0
                            schedule_status[k][3] = None
                            rem_fr_errd_jobs.append(k)

                            if k not in attempted_rerun.keys():
                                attempted_rerun[k] = 1
                            else:
                                attempted_rerun[k] += 1

                            print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
                                   'Attempt Rerun (' + str(attempted_rerun[k]) + '): ' + k)
                            prselogprint(level='Job',
                                         level2=None,
                                         status='AttemptRerun',
                                         fullrunfile=comp_runfile(x),
                                         name_alias=x.name_alias,
                                         ops_label=x.ops_label,
                                         message='Attempt: ' + str(attempted_rerun[k])
                                         )

            for k in rem_fr_errd_jobs:
                errored_jobs.remove(k)
        if len(errored_jobs) == 0 and len_prev_errd_jobs > 0:
            errors_present = False

        if not stop_gracefully:
            for x in schedule:
                schedule_status_key = sch_st_key(x)
                if x.bypassifexists is not None:
                    bypass_file = x.bypassifexists.split(',')
                    # stdprint(bypass_file)
                else:
                    bypass_file = 0

                # If not running and not complete and dependencies met or 'NONE' and jobs running < max concurrent
                if schedule_status[schedule_status_key][0] == 0 \
                        and schedule_status[schedule_status_key][1] == 0 \
                        and (set(x.depend).issubset(jobs_run) or x.depend[0].upper() == 'NONE') \
                        and jobs_cur_running < max_concurrent_jobs:
                    # When a job has previously completed but no LOOP signal present
                    if exist_signal_job(x, 'finished') and \
                            not exist_signal(filenamebase + '_' + schedule_status_key + '_LOOP.txt'):
                        print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
                               'FinishedPrev: ' + schedule_status_key)
                        prselogprint(level='Job',
                                     level2=None,
                                     status='FinishedPrev',
                                     fullrunfile=comp_runfile(x),
                                     name_alias=x.name_alias,
                                     ops_label=x.ops_label,
                                     message=None
                                     )
                        suppress_further_emails = complete_no_run(x, 'finishprev')
                        jobs_kicked_off += 1  # Count as kicked off for sake of continuing a schedule
                    elif bypass_file == 0:  # bypass attribute not set for schedule entry
                        suppress_further_emails = job_start(x, False)
                    else:  # bypass attribute set for schedule entry -- check existence
                        for byp_i in bypass_file:
                            if exist_signal(byp_i.strip()):
                                bypass_true = byp_i
                                break
                            else:
                                bypass_true = 0
                        if bypass_true != 0:  # Bypass signal found. Job will be bypassed
                            print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
                                   'Bypassed: ' + schedule_status_key + ' (SignalFound: ' + byp_i + ')')
                            prselogprint(level='Job',
                                         level2=None,
                                         status='Bypassed',
                                         fullrunfile=comp_runfile(x),
                                         name_alias=x.name_alias,
                                         ops_label=x.ops_label,
                                         message='SignalFound: (' + byp_i + ')'
                                         )
                            schedule_status[schedule_status_key][6] = 1
                            suppress_further_emails = complete_no_run(x,'bypass')
                        else:  # Bypass signal not found. Job will be started.
                            suppress_further_emails = job_start(x, False)
                    jobs_kicked_off += 1
                    jobs_cur_running += 1
                    # stdprint('Jobs kicked off: ' + str(jobs_kicked_off))
                    # stdprint('Jobs currently running: ' + str(jobs_cur_running))
                elif len(schedule) == 0:  # Go ahead and break out of loop if nothing left in schedule
                    break
                else:
                    pass
                ''' # Move this section up above to have better handling for manual signal intervention.
                elif exist_signal_job(x, 'finished'):  # When a job has previously completed
                    print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
                           'FinishedPrev: ' + schedule_status_key)
                    prselogprint(level='Job',
                                 level2=None,
                                 status='FinishedPrev',
                                 fullrunfile=comp_runfile(x),
                                 name_alias=x.name_alias,
                                 ops_label=x.ops_label,
                                 message=None
                                 )
                    complete_no_run(x, 'finishprev')
                    jobs_kicked_off += 1  # Count as kicked off for sake of continuing a schedule
                '''

        # stdprint('jobs kicked off: ' + str(jobs_kicked_off))

        cascade_to_sub_schedule = True
        if (exist_signal(filenamebase + '_STOPGRACEFUL.txt') or
                exist_signal(filenamebase + '_TEMPSTOP.txt') or
                exist_signal('sked_TEMPSTOP.txt') or
                exist_signal(filenamebase + '_STOPGRACEFULNC.txt') or
                exist_signal(schedule_alias_name + '_STOPGRACEFUL.txt')) and \
                        temp_stop == 0:
            # stdprint('stop graceful or tempstop signal found')

            print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
                   'Info: Stop Graceful or TempStop Signal Found. sked will exit after ' +
                                 'currently running jobs complete.')
            prselogprint(level='Schedule',
                         level2=None,
                         status='Info',
                         fullrunfile=None,
                         ops_label=None,
                         message='Stop Graceful or TempStop Signal Found. sked will exit after ' +
                                 'currently running jobs complete.'
                         )

            stop_gracefully = True
            temp_stop = 1
            if exist_signal(filenamebase + '_STOPGRACEFUL.txt'):
                remove_signal(filenamebase + '_STOPGRACEFUL.txt')
            if exist_signal(schedule_alias_name + '_STOPGRACEFUL.txt'):
                # print2('found ' + schedule_alias_name + '_STOPGRACEFUL.txt')
                remove_signal(schedule_alias_name + '_STOPGRACEFUL.txt')
            if exist_signal(filenamebase + '_STOPGRACEFULNC.txt'):
                remove_signal(filenamebase + '_STOPGRACEFULNC.txt')
                cascade_to_sub_schedule = False

            if cascade_to_sub_schedule:
                for k, v in schedule_status.items():
                    if v[0] == 1 and v[5] == 'schedule':
                        place_signal(k + '_STOPGRACEFUL.txt')
                    '''
                        for x in schedule:
                            if sch_st_key(x) == k:
                                place_signal(x.runfile + '_STOPGRACEFUL.txt')
                    # place_signal(k + '_STOPGRACEFUL.txt')  # needs to be filenamebase for subschedule instead of name=
                    '''

        if exist_signal(filenamebase + '_STOPKILL.txt'):
            remove_signal(filenamebase + '_STOPKILL.txt')
            suppress_further_emails = terminate_all_jobs()
            print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Exit: Jobs terminated immediately')
            prselogprint(level='Schedule',
                         level2=None,
                         status='StopKill',
                         fullrunfile=None,
                         ops_label=None,
                         message=filenamebase + '_STOPKILL.txt signal found. Jobs terminate immediately and exit.'
                         )
            sys.exit(42)

        # When an error occurs. Sked will try to get as far as possible on any parallel streams before completely
        # exiting. Check if current while loop cycle kicked off any jobs or has any still running in addition to
        # whether or not errors are present.
        if jobs_cur_running == 0 and jobs_kicked_off == 0 and errors_present == True:
            schedule_end_w_errors()

        # Reset jobs current running counter and re-build below.
        jobs_cur_running = 0
        # Loop to poll status of jobs to check for completion
        for k, v in schedule_status.items():
            if v[0] == 1:  # Job flagged as running/started
                if v[3] is None:  # Skip polling if long_running_kill or dependency_collection has manually set a value
                    v[3] = schedule_status_popen[v[2]].poll()  # Poll job to see if finished
                if v[3] is None:  # Job still running
                    jobs_cur_running += 1

                    # Check if long running here. When alerts on, not already alerted on, every 60sec,
                    # past durations available, minimum number of past timings threshold met, k is a given job
                    if long_running_alerting == 1 and \
                                    k not in long_running_alert and \
                                            total_time % 60 == 0 and \
                                    k in avg_past_duration and \
                                    times_per_jobs[k] >= long_running_min_times:
                        # Available dictionaries for timings & creating a long running function
                        # avg_past_duration[k] - average duration of last runs*
                        # times_per_jobs[k] - number of durations available for given job
                        # max_past_duration[k] - maximum past duration of last runs*
                        # min_past_duration[k] - minimum past duration of last runs*
                        # *runs = max(times_per_jobs[k], min(num_dur_files, optimize_concurrency_files)) runs
                        current_elapsed_time = datetime.datetime.now() - v[4]  # Elapsed time thus far

                        # Function to qualify if long running
                        if (current_elapsed_time.total_seconds() > long_running_min) and \
                                (avg_past_duration[k] + int(avg_past_duration[k] ** long_running_power)) < \
                                        current_elapsed_time.total_seconds() and v[5] != 'schedule':
                            long_running_alert.append(k)  # Append to list so we dont alert every minute on a job

                            for x in schedule:
                                if k == sch_st_key(x):
                                    if x.long_running_kill is not None: # If not none then 'Y'
                                        if os.name == 'posix':
                                            # temppid = schedule_status_popen[schedule_status[k][2]].pid
                                            os.killpg(os.getpgid(schedule_status_popen[schedule_status[k][2]].pid),
                                                      signal.SIGKILL)
                                        else:
                                            schedule_status_popen[schedule_status[k][2]].terminate()
                                        v[3] = 137
                                        print2(datetime.datetime.now().strftime(
                                            "%Y-%m-%d %H:%M:%S - ") + 'Long Running Kill: ' + k +
                                              ' has been killed for running for longer than usual.')
                                        # Send email to notify of long running job
                                        suppress_further_emails = send_email_notify(
                                            'LONG RUNNING KILL: ' + on_machine_email + ' - ' + filenamebase + ' - ' + k,
                                            'Machine: ' + on_machine_email + '\n' +
                                            'Schedule: ' + filenamebase + '\n' +
                                            'Job: ' + k + '\n' +
                                            'Has Been Running Since: ' + v[4].strftime("%Y-%m-%d %H:%M:%S") + '\n' +
                                            'Job process has been killed.')
                                    else:
                                        print2(datetime.datetime.now().strftime(
                                            "%Y-%m-%d %H:%M:%S - ") + 'Long Running: ' + k +
                                               ' has been running for longer than usual.')
                                        # Send email to notify of long running job
                                        suppress_further_emails = send_email_notify(
                                            'LONG RUNNING: ' + on_machine_email + ' - ' + filenamebase + ' - ' + k,
                                            'Machine: ' + on_machine_email + '\n' +
                                            'Schedule: ' + filenamebase + '\n' +
                                            'Job: ' + k + '\n' +
                                            'Has Been Running Since: ' + v[4].strftime("%Y-%m-%d %H:%M:%S"))

                elif 0 <= v[3] <= v[7]:  # Job finished successfully
                    '''
                    v[1] = 1  # Flag job as finished
                    v[0] = 0  # Flag job as not running
                    job_end = datetime.datetime.now()
                    # Duration will always be 1 second off due to loop sleep polling period
                    job_dur = (job_end - v[4])  # - datetime.timedelta(seconds=1)
                    print2(job_end.strftime("%Y-%m-%d %H:%M:%S - ")+'Finished: ' + k +
                           ' (Success rc=' + str(v[3]) + ') Duration: ' + str(job_dur))
                    jobs_run.append(k)  # Add to completed list for dependency checks in job start loop
                    # Add to duration log
                    if signal_clear_only is False:
                        durprint(name=k, duration=int(job_dur.total_seconds()))
                    # Remove entries from schedule as they are run. Do this outside first loop so conflicts don't occur
                    for x in schedule:
                        schedule_status_key = sch_st_key(x)
                        if schedule_status_key == k:
                            schedule.remove(x)
                            if not stop_gracefully or x.runfiletype != 'schedule':
                                place_signal_job(x, 'finished')
                                prselogprint(level='Job',
                                             level2=None,
                                             status='Finished',
                                             fullrunfile=comp_runfile(x),
                                             name_alias=x.name_alias,
                                             ops_label=x.ops_label,
                                             message=None
                                             )
                                suppress_further_emails = send_email_notify_custom(x, 'Finished')
                                if x.notify == '1' or notify_all_override:
                                    suppress_further_emails = send_email_notify(
                                        'FINISHED: ' + on_machine_email + ' - ' + filenamebase + ' - ' +
                                        schedule_status_key,
                                        'Machine: ' + on_machine_email + '\n' +
                                        'Schedule: ' + filenamebase + '\n' +
                                        'Job Finished: ' + schedule_status_key)

                                if plugin_to_load is not None and hasattr(sked_plugin, 'on_job_finished'):
                                    sked_plugin.on_job_finished(filename, check_schedule, x, schedule_status, config_file)
                    '''
                    v[0] = 0  # Flag job as not running

                    # Cleanup stdout reader thread since process has stopped
                    if v[8] is not None:  # if standard out exists
                        stdout_reader, stdout_queue = v[8]
                        stdout_reader.join()

                    job_end = datetime.datetime.now()
                    # Duration will always be 1 second off due to loop sleep polling period
                    job_dur = (job_end - v[4])  # - datetime.timedelta(seconds=1)
                    print2(job_end.strftime("%Y-%m-%d %H:%M:%S - ") + 'Finished: ' + k +
                           ' (Success rc=' + str(v[3]) + ') Duration: ' + str(job_dur))
                    if exist_signal(filenamebase + '_' + k + '_LOOP.txt'):
                        pass
                    else:
                        v[1] = 1  # Flag job as finished
                        jobs_run.append(k)  # Add to completed list for dependency checks in job start loop
                        # Add to duration log
                        if signal_clear_only is False and v[5] != 'dependency_collection':
                            durprint(name=k, duration=int(job_dur.total_seconds()))
                    for x in schedule:
                        schedule_status_key = sch_st_key(x)
                        if schedule_status_key == k:
                            if v[8] is not None:  # if standard out exists
                                if printStdOut != "Off":  # jazzha
                                    stdoutlog_file_name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_") + \
                                                          os.path.basename(exefile_path) + '_' + \
                                                          os.path.basename(filename) + '_' + schedule_status_key + \
                                                          '.stdout.log'

                                    # Join up all elements that were added to the stdout_queue by new line. This is a
                                    # blocking call, so if the subprocess hasn't finished, then this will wait until
                                    # complete. Only call using this method if we know the process is complete
                                    stdout_reader, stdout_queue = v[8]
                                    stdout_dump = ''.join(iter(stdout_queue.get, None))

                                    with open(logpath + stdoutlog_file_name, 'w') as stdoutlog:
                                        stdoutlog.write(stdout_dump)

                                    if stdout_dump.count('\n') > 18:
                                        stdout_display = 'STDOUT (over 20 lines long): ' + logpath + \
                                                         stdoutlog_file_name
                                    else:
                                        stdout_display = 'STDOUT (' + logpath + stdoutlog_file_name + '): \n\n' + \
                                                     stdout_dump
                            if not exist_signal(filenamebase + '_' + k + '_LOOP.txt'):
                                schedule.remove(x)
                            if not stop_gracefully or x.runfiletype != 'schedule':
                                place_signal_job(x, 'finished')
                                prselogprint(level='Job',
                                             level2=None,
                                             status='Finished',
                                             fullrunfile=comp_runfile(x),
                                             name_alias=x.name_alias,
                                             ops_label=x.ops_label,
                                             message=None
                                             )
                                suppress_further_emails = send_email_notify_custom(x, 'Finished')
                                if x.notify == '1' or notify_all_override:
                                    suppress_further_emails = send_email_notify(
                                        'FINISHED: ' + on_machine_email + ' - ' + filenamebase + ' - ' +
                                        schedule_status_key,
                                        'Machine: ' + on_machine_email + '\n' +
                                        'Schedule: ' + filenamebase + '\n' +
                                        'Job Finished: ' + schedule_status_key)

                                if plugin_to_load is not None and hasattr(sked_plugin, 'on_job_finished'):
                                    sked_plugin.on_job_finished(filename, check_schedule, x, schedule_status,
                                                                config_file)
                                if exist_signal(filenamebase + '_' + k + '_LOOP.txt'):
                                    prselogprint(level='Job',
                                                 level2=None,
                                                 status='Loop',
                                                 fullrunfile=comp_runfile(x),
                                                 name_alias=x.name_alias,
                                                 ops_label=x.ops_label,
                                                 message=None
                                                 )
                    if exist_signal(filenamebase + '_' + k + '_LOOP.txt'):
                        print2(job_end.strftime("%Y-%m-%d %H:%M:%S - ") + 'Loop Signal Found: ' + k)

                elif v[3] > v[7] and v[1] == 0:  # Errors present, v[3] = rc, v[7] = max_rc for success
                    v[1] = 1  # Flag as finished
                    v[0] = 0  # Flag as not running

                    # Cleanup stdout reader thread since process has stopped
                    if v[8] is not None:  # if standard out exists
                        stdout_reader, stdout_queue = v[8]
                        stdout_reader.join()

                    errored_jobs.append(k)  # Add to errored jobs so checking can begin for restart signals.
                    for x in schedule:
                        schedule_status_key = sch_st_key(x)
                        if schedule_status_key == k:
                            if cfg_scheduletype_errors == 'Y' or x.runfiletype != 'schedule':
                                stdout_display = ''  # initialize to empty string so emails will still work
                                stdout_dump = ''  # initialize dump only
                                if v[8] is not None:  # if standard out exists
                                    if v[5] != 'schedule':  # if entry type is not a sub-schedule
                                        '''
                                        if v[5] == 'sas':
                                            stdout_display = 'STDOUT: \n\n' + v[8].read().decode('utf-8')
                                        else:  # shell entry type
                                            stdout_display = v[8].read().decode('utf-8')
                                            if stdout_display.count('\n') > 18:  # if stdout is long
                                                stdoutlog_file_name = datetime.datetime.now().strftime(
                                                    "%Y%m%d_%H%M%S_") + os.path.basename(
                                                    exefile_path) + '_' + os.path.basename(
                                                    filename) + '_' + schedule_status_key + '.stdout.log'
                                                with open(logpath + stdoutlog_file_name, 'w') as stdoutlog:
                                                    stdoutlog.write(stdout_display)

                                                stdout_display = 'STDOUT (over 20 lines long): ' + \
                                                                 logpath + stdoutlog_file_name
                                            else:  # stdout is not long. put in email as is
                                                stdout_display = 'STDOUT: \n\n' + stdout_display
                                        '''
                                        stdoutlog_file_name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_") + \
                                                              os.path.basename(exefile_path) + '_' + \
                                                              os.path.basename(filename) + '_' + schedule_status_key + \
                                                              '.stdout.log'

                                        # Join up all elements that were added to the stdout_queue by new line. This is
                                        # a blocking call, so if the subprocess hasn't finished, then this will wait
                                        # until complete. Only call using this method if we know the process is
                                        # complete.
                                        stdout_reader, stdout_queue = v[8]
                                        stdout_dump = ''.join(iter(stdout_queue.get, None))

                                        with open(logpath + stdoutlog_file_name, 'w') as stdoutlog:
                                            stdoutlog.write(stdout_dump)

                                        if stdout_dump.count('\n') > 18:
                                            stdout_display = 'STDOUT (over 20 lines long): ' + logpath + \
                                                             stdoutlog_file_name
                                        else:
                                            stdout_display = 'STDOUT (' + logpath + stdoutlog_file_name +'): \n\n' + \
                                                             stdout_dump
                                # print('hello')
                                # print(suppress_further_emails)
                                if (k not in attempted_rerun and x.attempt_rerun is not None) or \
                                        (k in attempted_rerun and attempted_rerun[k] is not None and
                                                 x.attempt_rerun > attempted_rerun[k]):
                                    if x.notify == '1':
                                        suppress_further_emails = send_email_notify('ERROR: ' + on_machine_email + ' - ' +
                                                                                    filenamebase + ' - ' + k +
                                                                                    ' - Will Attempt Re-run',
                                                                                   'Machine: ' + on_machine_email + '\n' +
                                                                                   'Schedule: ' + filenamebase + '\n' +
                                                                                   'Error Running: ' + k + '\n' +
                                                                                   'Will Attempt Re-Run\n' +
                                                                                   'Return Code: ' + str(v[3]) + '\n\n\n' +
                                                                                    stdout_display)
                                else:
                                    suppress_further_emails = send_email_notify('ERROR: ' + on_machine_email + ' - ' +
                                                                                filenamebase + ' - ' + k,
                                                                                'Machine: ' + on_machine_email + '\n' +
                                                                                'Schedule: ' + filenamebase + '\n' +
                                                                                'Error Running: ' + k + '\n' +
                                                                                'Return Code: ' + str(v[3]) + '\n\n\n' +
                                                                                stdout_display)
                            if (k not in attempted_rerun and x.attempt_rerun is not None) or \
                                        (k in attempted_rerun and attempted_rerun[k] is not None and
                                                 x.attempt_rerun > attempted_rerun[k]):
                                print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Error: ' + str(k) +
                                       ' (Failure rc=' + str(v[3]) + ') - Attempt to Re-run')
                                prselogprint(level='Job',
                                             level2=None,
                                             status='Error',
                                             fullrunfile=comp_runfile(x),
                                             name_alias=x.name_alias,
                                             ops_label=x.ops_label,
                                             message='attempt_rerun'
                                             )
                            else:
                                print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Error: ' + str(k) +
                                       ' (Failure rc=' + str(v[3]) + ')')
                                prselogprint(level='Job',
                                             level2=None,
                                             status='Error',
                                             fullrunfile=comp_runfile(x),
                                             name_alias=x.name_alias,
                                             ops_label=x.ops_label,
                                             message=None
                                             )
                            suppress_further_emails = send_email_notify_custom(x, 'Error')
                            place_signal_job(x, 'ERROR')
                            if plugin_to_load is not None and hasattr(sked_plugin, 'on_job_error'):
                                sked_plugin.on_job_error(filename, check_schedule, x, schedule_status, config_file)
                    # stop_gracefully = True
                    errors_present = True
                    # sys.exit(42)
                    # print2(schedule_status_popen[v[2]].communicate()[0].decode())
                    # terminate_all_jobs()
            elif v[3] == -1:  # When a job has previously completed on a previous run
                jobs_run.append(k)
                for x in schedule:
                    if sch_st_key(x) == k:
                        schedule.remove(x)
                        if not stop_gracefully:
                            # place_signal_job(x, 'finished')  # commented so finishedprev doesn't get new timestmp
                            if v[6] == 1:  # if job was bypassed.
                                place_signal_job(x, 'finished')
                                place_signal_job(x, 'bypassed')

        if stop_gracefully:
            jobs_running = 0
            for k, v in schedule_status.items():
                jobs_running = jobs_running+v[0]
            if jobs_running == 0:
                if errors_present:
                    stdprint('stop gracefully, no jobs running, errors present')
                    schedule_end_w_errors()
                else:
                    if exist_signal(filenamebase + '_TEMPSTOP.txt'):
                        print2(datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S - ") + 'Exit: TEMPSTOP Signal Present - Stop Schedule Gracefully')
                        prselogprint(level='Schedule',
                                     level2=None,
                                     status='TempStop',
                                     fullrunfile=None,
                                     ops_label=None,
                                     message=filenamebase + '_TEMPSTOP.txt or sked_TEMPSTOP.txt signal found.'
                                     )
                        suppress_further_emails = send_email_notify('TEMPSTOP PRESENT: ' + on_machine_email + ' - ' +
                                                                    filenamebase, 'Schedule ' + filenamebase +
                                                                    ' stopped gracefully by ' + filenamebase +
                                                                    '_TEMPSTOP.txt or sked_TEMPSTOP.txt signal on ' +
                                                                    on_machine_email)
                    else:
                        print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
                               'Exit: Stop Schedule Graceful Signal Found')
                        prselogprint(level='Schedule',
                                     level2=None,
                                     status='StopGraceful',
                                     fullrunfile=None,
                                     ops_label=None,
                                     message=filenamebase + '_STOPGRACEFUL.txt signal found.'
                                     )
                        suppress_further_emails = send_email_notify('USER STOPPED GRACEFUL: ' + on_machine_email +
                                                                    ' - ' + filenamebase, 'Schedule ' + filenamebase +
                                                                    ' stopped gracefully by signal on ' +
                                                                    on_machine_email)
                    place_signal(filenamebase + '-stopped_gracefully.sig')
                    sys.exit(0)

        total_time += 1
        sleep(1)

# Place schedule ended signal
if not signal_clear_only and not stop_gracefully:
    place_signal(filenamebase + '-finished.sig')
    print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Exit: Schedule Finished')
    prselogprint(level='Schedule',
                 level2=None,
                 status='Finished',
                 fullrunfile=None,
                 ops_label=None,
                 message=None
                 )
    if exist_signal(filenamebase + '_ONEandSTOP.txt') or exist_signal('sked_ONEandSTOP.txt'):
        if not exist_signal(filenamebase + '_TEMPSTOP.txt') and not exist_signal('sked_TEMPSTOP.txt'):
            print2(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") +
                'Info: ONEandSTOP Signal Found. Placing TEMPSTOP Signal.')
            prselogprint(level='Schedule',
                         level2=None,
                         status='Info',
                         fullrunfile=None,
                         ops_label=None,
                         message='ONEandSTOP Signal Found. Placing TEMPSTOP Signal.'
                         )
        place_signal(filenamebase + '_TEMPSTOP.txt')

    if notify_finish == 1 or notify_all_override:
        suppress_further_emails = send_email_notify('FINISHED: ' + on_machine_email + ' - ' + filenamebase,
                                                    'Schedule ' + filenamebase +
                                                    ' finished on ' + on_machine_email + ' successfully')

    if plugin_to_load is not None and hasattr(sked_plugin, 'on_schedule_finish') and signal_clear_only is False:
        sked_plugin.on_schedule_finish(filename, check_schedule, config_file)

# atexit.register(terminate_all_jobs())  # Not needed.
# print2(schedule)
# print2(jobs_run)
