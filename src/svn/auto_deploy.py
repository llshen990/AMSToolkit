#!/usr/bin/python

# @author owhoyt
# This file will auto-update the svn repository

import os.path, sys, getopt, traceback, subprocess, re, socket, ConfigParser, time, types, commands

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../"))
sys.path.append(APP_PATH)

from lib.Validators import EmailValidator, FileExistsValidator
from lib.Helpers import ProcCheck, SASEmail

##### Read Config / Globals #####
config = ConfigParser.ConfigParser()
config.read(os.path.abspath(os.path.dirname(__file__)) + '/svn.cfg')
svn_user = config.get('DEFAULT', 'svn_user').strip()
svn_pass = config.get('DEFAULT', 'svn_pass').strip()
svn_cache_log_file = config.get('DEFAULT', 'svn_log_cache_file_loc').strip()
svn_update_log_file = config.get('DEFAULT', 'svn_update_cache_file_loc').strip()
if not svn_pass or not svn_user or not svn_cache_log_file:
    print "[ERROR] ./svn.cfg file not found!"
    sys.exit(2)

execute_svn_update = True
send_email_enabled = True

##### End Config / Globals #####

def print_usage():
    """ This method will print the usage of the auto_deploy.py file
    :return: none
    """
    print '[USAGE1] python auto_deploy.py -l <true|false> -e <email list|empty> -p <path-to-repo-on-fs> -d <true|false>'
    print '*Note: email addresses must be separated by commas, spaces or semicolons.'
    print "[EXAMPLE] python auto_deploy.py -l true -e 'something@sdafjdlsjdlsjf.com' -p '/some/path' -d true"
    print "[EXAMPLE] python auto_deploy.py -l false -e '' -p '/some/path' -d false"
    return False

def print_debug(debug, msg):
    """
    This function will print a debug message if debug is on
    :param debug: bool
    :param msg: str
    :return: bool
    """
    if debug:
        print '[DEBUG] ' + str(msg).strip()

    return True

def write_cache_file(debug, svn_cache_log_file_in, data):
    """
    This function will write data to a cache file so that we don't keep sending emails over and over and over for conflicts.
    :param debug: bool
    :param svn_cache_log_file_in: str
    :param data: mixed
    :return: bool
    """
    print_debug(debug, "in function: write_cache_file")
    f = open(svn_cache_log_file_in, 'w+')
    f.write(data)
    f.close()
    return True

def is_cache_change(debug, svn_cache_log_file_in, data_new):
    """
    This function will determine if the SVN log changed from this time to last time.
    :param debug: bool
    :param svn_cache_log_file_in: str
    :param data_new: mixed
    :return: bool
    """
    print_debug(debug, 'in function: is_log_change')
    file_exists_validator = FileExistsValidator(True)
    if not file_exists_validator.validate(svn_cache_log_file_in):
        print_debug(debug, svn_cache_log_file_in + ' does not exist yet, touching...')
        open(svn_cache_log_file_in, 'a').close()

    with open(svn_cache_log_file_in, 'r') as tmp_file:
        data_old = tmp_file.read()

    return not data_old.strip() == data_new.strip()

def get_svn_host_base_path(debug, path):
    """
    This method will get the base SVN URL from the given path.
    :param debug: bool
    :param path: str
    :return: str
    """
    svn_info_proc = subprocess.Popen(("svn", "info", path), stdout=subprocess.PIPE)
    grep = subprocess.Popen(('grep', 'URL'), stdin=svn_info_proc.stdout, stdout=subprocess.PIPE)
    awk = subprocess.Popen(('awk', '{print $NF}'), stdin=grep.stdout, stdout=subprocess.PIPE)
    svn_base_path = awk.communicate()[0].strip()
    print_debug(debug, 'svn_base_path: ' + svn_base_path)
    return svn_base_path

def get_consolidated_conflict_list(debug, conflict_list_in):
    """
    This method will create a single tuple to return due to multiple patterns for conflicts.
    :param debug: bool
    :param conflict_list_in: dict
    :return:
    """
    print_debug(debug, 'In get_consolidated_conflict_list: ' + str(conflict_list_in))
    ret_tuple = ()
    for conflict_pattern_1, conflict_pattern_2 in conflict_list_in:
        conflict_pattern_1 = str(conflict_pattern_1).strip()
        conflict_pattern_2 = str(conflict_pattern_2).strip()
        if conflict_pattern_1:
            ret_tuple = ret_tuple + (conflict_pattern_1,)
        if conflict_pattern_2:
            ret_tuple = ret_tuple + (conflict_pattern_2,)

    return ret_tuple

def remove_conflict_files(debug, file_list, conflict_list):
    """
    This method will remove incoming files that also are conflicted.
    :param debug: bool
    :param file_list: dict
    :param conflict_list: tuple
    :return:
    """
    print_debug(debug, 'in remove_conflict_files')
    ret_dict = []
    for rev_and_file in file_list:
        file_path = rev_and_file[1]
        if file_path in conflict_list:
            continue

        ret_dict.append(rev_and_file)
    return ret_dict

def get_svn_log_messages(debug, path, base_svn_url):
    """
    This method will get the SVN log messages for all incoming updates.  This will handle mixed revisions as well as record incoming conflicts.
    :param debug: bool
    :param path: str
    :param base_svn_url: str
    :return: str
    """
    global svn_user, svn_pass, execute_svn_update, svn_cache_log_file
    incoming_rev_list = {}
    file_list_str = ''
    # print_debug(debug, 'svn_status_out: \n' + '%s %s %s %s %s %s %s %s %s %s' % ("svn", "status", "-u", '--username', svn_user, '--password', svn_pass, '--non-interactive', '--no-auth-cache', path))
    svn_status_out = subprocess.Popen(("svn", "status", "-u", '--username', svn_user, '--password', svn_pass, '--non-interactive', '--no-auth-cache', path), stdout=subprocess.PIPE)
    pattern = re.compile("^Status against revision:\s+([\d]+)$")
    svn_status_out_txt = svn_status_out.communicate()[0]
    svn_status_out_txt_4_incoming = commands.getoutput("svn status -u --username " + svn_user + " --password " + svn_pass + " --non-interactive --no-auth-cache " + path + " | grep '*'")
    current_revision = pattern.findall(svn_status_out_txt)
    is_svn_log_change = is_cache_change(debug, svn_cache_log_file, svn_status_out_txt)
    print 'is_svn_log_change: %r' % is_svn_log_change
    write_cache_file(debug, svn_cache_log_file, svn_status_out_txt)
    if current_revision:
        print "[SUCCESS] Already at latest revision: " + str(current_revision[0])
        return True

    incoming_rev_pattern = re.compile('\s+\*\s+(\d+)\s+([\w\./\-\s_]+)\n')
    conflict_rev_pattern = re.compile('C\s+\d+\s+([\w\./\-\s_]+)\n|C\s+\*\s+\d+\s+([\w\./\-\s_]+)\n')
    conflict_list_raw = conflict_rev_pattern.findall(svn_status_out_txt)
    conflict_list = get_consolidated_conflict_list(debug, conflict_list_raw)

    rev_2_file_list_raw = incoming_rev_pattern.findall(svn_status_out_txt_4_incoming + '\n')
    rev_2_file_list = remove_conflict_files(debug, rev_2_file_list_raw, conflict_list)
    print_debug(debug, 'svn_status_out_txt:\n\n' + svn_status_out_txt + '\n\n')
    print_debug(debug, 'conflict_list:' + str(conflict_list))
    print_debug(debug, 'rev_2_file_list:\n' + str(rev_2_file_list))
    if (not rev_2_file_list and not conflict_list) or (not is_svn_log_change):
        execute_svn_update = False
        print_debug(debug, 'No files to update and no conflict or svn log cache has not changed')
        return ''
    elif not rev_2_file_list and conflict_list and is_svn_log_change:
        execute_svn_update = False
        print_debug(debug, 'No actionable incoming revisions...')
        return '[ERROR] There are conflicts in the following files, but otherwise no updates:' + "\n".join(conflict_list) + "\n\n" + svn_status_out_txt

    for rev_and_file in rev_2_file_list:
        rev = rev_and_file[0]
        file_path = rev_and_file[1]

        print_debug(debug, rev + " => " + file_path)

        if rev not in incoming_rev_list:
            incoming_rev_list[rev] = []

        if file_list_str:
            file_list_str += " "

        incoming_rev_list[rev].append(file_path.replace(path, ''))

    print_debug(debug, 'rev_2_file_list:\n' + str(rev_2_file_list))
    print_debug(debug, 'incoming_rev_list:\n' + str(incoming_rev_list))

    # now we need to loop through the incoming rev_list
    svn_log_out = ''

    if conflict_list:
        svn_log_out += "[ERROR] Conflicts in the following files:\n" + " ".join(conflict_list)

    for rev, file_list in incoming_rev_list.iteritems():
        dir_list = file_list[:]
        if path[:-1] in dir_list:
            dir_list.remove(path[:-1])
        for f in file_list:
            if os.path.isfile(path + f) or (os.path.isdir(path + f) and svn_status_out_txt_4_incoming.count(f + '/') == 0):
                dir_list.remove(f)
                f_dir = os.path.dirname(path + f).replace(path, '')
                if f_dir not in dir_list:
                    dir_list.append(f_dir)

        rev_list_str = str(int(rev) + 1) + ":HEAD"
        # print_debug(debug, 'log command: \n' + '%s %s %s %s %s %s %s %s %s %s %s %s %s' % ('svn', 'log', '-v', '--username', svn_user, '--password', svn_pass, '--non-interactive', '--no-auth-cache', '-r', rev_list_str, base_svn_url, " ".join(file_list)))
        arg_list = ['svn', 'log', '-v', '--username', svn_user, '--password', svn_pass, '--non-interactive', '--no-auth-cache', '-r', rev_list_str, base_svn_url]
        arg_list.extend(dir_list)
        svn_info_proc = subprocess.Popen(arg_list, stdout=subprocess.PIPE)
        # svn_info_proc = subprocess.Popen(('svn', 'log', '-v', '-r', rev_list_str, base_svn_url, " ".join(file_list)), stdout=subprocess.PIPE)
        if svn_log_out:
            svn_log_out += "\n\n============================ [NEW FILE LIST] ============================\n\n"
        svn_log_out += "[CHANGE LOG FOR]\n" + "\n".join(dir_list) + "\n\n"
        svn_log_out += svn_info_proc.communicate()[0]
    print_debug(debug, "svn_log_proc:\n" + svn_log_out)
    return svn_log_out

def svn_update(debug, path):
    """
    This method will perform an svn update and return the output of the svn update command.
    :param debug: bool
    :param path: str
    :return: str
    """
    print_debug(debug, "in func: svn_update")
    global svn_user, svn_pass, execute_svn_update, svn_update_log_file, send_email_enabled
    if not execute_svn_update:
        return ''
    svn_update_proc = subprocess.Popen(["svn", "update", '--username', svn_user, '--password', svn_pass, '--non-interactive', '--no-auth-cache', path], stdout=subprocess.PIPE)
    svn_update_out = str(svn_update_proc.communicate()[0]).strip()
    # print_debug(debug, "svn_update_out:\n" + svn_update_out)
    if not is_cache_change(debug, svn_update_log_file, svn_update_out):
        send_email_enabled = False
        print_debug(debug, 'The svn update log cache comparison to the incoming svn update output has not changed.  Disabling email send...')
        return ''
    else:
        write_cache_file(debug, svn_update_log_file, svn_update_out)
    return svn_update_out

def main(argv):
    """
    This method will execute the main method of this script which is to perform an SVN update and then email out pending the script args.
    :param argv: args
    :return: bool
    """
    try:
        include_log = False
        email_addresses = ''
        debug = False
        path = ''
        opts, args = getopt.getopt(argv, "hl:e:p:d:")
        for opt, arg in opts:
            if opt == '-h':
                print_usage()
            elif opt == "-l" and arg == "true":
                include_log = True
            elif opt == "-e":
                try:
                    email_validator = EmailValidator(True)
                    email_addresses = email_validator.validate_email_list(arg, True)
                    if email_validator.get_errors():
                        email_validator.format_errors()
                        return False
                except Exception as e:
                    print "Exception: " + str(e)
                    return False
            elif opt == '-d' and arg == 'true':
                debug = True
            elif opt == '-p':
                path = str(arg).strip()
                path = os.path.join(path, '')

        if not path:
            print '[ERROR] the path of the SVN repo on the file system is required'
            print_usage()
            return False

        print_debug(debug, 'include_log: ' + str(include_log))
        print_debug(debug, 'email_addresses: ' + str(email_addresses))
        print_debug(debug, 'debug: ' + str(debug))
        print_debug(debug, 'path: ' + str(path))

        email_message = ''
        log_message = ''
        if include_log and email_addresses:
            svn_host_base_url = get_svn_host_base_path(debug, path)
            log_message = get_svn_log_messages(debug, path, svn_host_base_url)
            if type(log_message) == types.BooleanType:
                log_message = ''

            print_debug(debug, 'log_message:\n' + str(log_message))

        if include_log and not log_message:
            print "[SUCCESS] No incoming updates"
            return True
        svn_update_out = svn_update(debug, path)
        update_pattern = '^At\s+revision\s+([0-9]+)\.$'
        svn_update_pattern = re.compile(update_pattern)

        hostname = str(socket.gethostname()).strip()

        if not re.findall(svn_update_pattern, svn_update_out) and execute_svn_update:
            # clear log file cache
            write_cache_file(debug, svn_cache_log_file, '')
            print_debug(debug, 'Did not match pattern: ' + update_pattern)
            email_message = "SVN Auto-Deploy has found new incoming changes on host " + hostname + ".  Please see below:\n\n"
            email_message += svn_update_out
            if log_message:
                email_message += "\n\n" + log_message
        elif log_message.find('[ERROR]') >= 0:
            print_debug(debug, 'Found Error in log message')
            email_message = "SVN Auto-Deploy has found no incoming changes on " + hostname + ".  However, there are conflicts:\n\n"
            email_message += log_message
        else:
            print 'No email being sent, here is the svn update output:\n'
            print svn_update_out

        if email_addresses and email_message and send_email_enabled:
            print_debug(debug, '[SENDING EMAIL]')
            sas_email = SASEmail()
            sas_email.set_from('replies-disabled@sas.com')
            sas_email.set_to(email_addresses)
            sas_email.set_subject("[" + hostname + "] SVN Auto-Deploy Change")
            sas_email.set_text_message(email_message)
            sas_email.send()
            print '[EMAIL SENT] Finished process.'
        elif not send_email_enabled:
            print '[NO EMAIL] Email was disabled per logic in this script.  Most likely in attempt to rate limit emails and not SPAM for same exact output with no updates being applied.'
    except getopt.GetoptError:
        # throw error on any get options error.
        print_usage()
        return False
    except Exception as e:
        print "Caught exception running auto_deploy:\n"
        print str(e)
        traceback.print_exc()
        return False

# this is how we invoke the main method to start everything off and we pass in argv from sys.
if __name__ == "__main__":
    print '----------- Starting Run ' + str(time.strftime("%Y-%m-%d %H:%M:%S")) + ' -----------'
    procCheck = ProcCheck(__file__, os.getpid())
    procCheck.am_i_already_running()
    ret_val = main(sys.argv[1:])
    procCheck.delete_lock_file()
    sys.exit(ret_val)