import StripHtmlTags
import os
import subprocess
import sys

class ProcCheck(object):
    """
    This method will ensure that a script (process) cannot be running more than one instance at a time.
    Attributes:
        __myFullFileNameWithPath: The full filename with path.
        __myPID: The PID of the calling file.
        __baseName: The basename of the file without path or extension.
        __lockFile: The location of the lock file.
        __arrExtraGrep: This is an array of extra parameters we can add to the GREP if we want to.  This would support multiple environments running on the same BOX.
    """

    def __init__(self, filename, pid, extra_lock_file_str=None):
        """
        This method will construct the ProcCheck class.
        Args:
            filename: str - the file that we want to check if it is already running or not.
            pid: int - the pid of the calling file
        """
        if not os.environ.get('_USER'):
            who_am_i = subprocess.Popen('whoami', stdout=subprocess.PIPE)
            os.environ['_USER'] = str(who_am_i.communicate()[0]).strip()

        self.__myFullFileNameWithPath = str(filename).strip()
        self.__myPID = int(pid)
        self.__baseName = os.path.basename(filename)
        # self.__lockFile = os.path.abspath((os.path.dirname(filename.rstrip(os.pathsep)) or '.') + '/__' + self.__baseName + '_' + os.environ['_USER'] + '__.lock')
        if not extra_lock_file_str:
            self.__lockFile = os.path.abspath(os.path.join((os.path.dirname(filename.rstrip(os.pathsep)) or '.'), '__' + self.__baseName + '_' + os.environ['_USER'] + '__.lock'))
        else:
            self.__lockFile = os.path.abspath(os.path.join((os.path.dirname(filename.rstrip(os.pathsep)) or '.'), '__' + self.__baseName + '_' + os.environ['_USER'] + '_' + str(extra_lock_file_str).strip() + '__.lock'))
        self.__arrExtraGrep = []

    def add_extra_grep(self, string_to_grep, exclude=False):
        """
        This will add strings to an extra grep.
        Args:
            string_to_grep: String to grep
            exclude: include or exclude (1/0)

        Returns: bool
        """
        try:
            strip_tags = StripHtmlTags.StripHtmlTags()
            string_to_grep = strip_tags.strip(str(string_to_grep).strip())
            self.__arrExtraGrep.append({
                'string': string_to_grep,
                'exclude': True if exclude == True else False
            })

            return True
        except Exception as e:
            print 'There has been a problem adding an extra grep: ' + str(e)
            return False

    def __build_extra_grep(self):
        """
        This method will build the extra grep string based upon the extra grep array.
        Returns: list
        """
        extra_grep_str = ['grep']

        if len(self.__arrExtraGrep) > 0:
            for extraGrep in self.__arrExtraGrep:
                if extraGrep['exclude']:
                    extra_grep_str.append('-v')
                extra_grep_str.append(extraGrep['string'])

        return extra_grep_str

    def am_i_already_running(self):
        """
        This method will determine if the process is already running.  If it is, it will throw a sys.exit(1) and halt the script execution.
        :return: True
        """
        try:
            if self.__myFullFileNameWithPath == '':
                print "[ERROR] No file name passed to check if it is running"
                sys.exit(1)

            if self.__myPID < 1:
                print "[ERROR] No PID passed"
                sys.exit(1)

            if os.path.exists(self.__lockFile):
                lock_file_pid = open(self.__lockFile).read(1000).strip()
                if os.path.exists('/proc/' + lock_file_pid):
                    print "[ERROR] " + self.__myFullFileNameWithPath + " is already running check #1 - lock file: " + self.__lockFile
                    sys.exit(1)

            extra_grep_string = self.__build_extra_grep()
            # out = subprocess.call(["ps -ef | grep -i $0 | grep -v $1 $2 | grep -v grep | grep -v /bin/sh | awk '{ print $2 }'", self.__baseName, str(self.__myPID), extra_grep_string], shell=True)
            # out = subprocess.call(["ps -ef", "| grep -i " + self.__baseName, '| grep -v ' + str(self.__myPID) + ' ' + extra_grep_string, '| grep -v grep', '| grep -v /bin/sh', "| awk '{ print $2 }'"], shell=True)
            ps = subprocess.Popen(("ps", '-ef'), stdout=subprocess.PIPE)
            # print ps.communicate()[0]
            # print exit()
            grep1 = subprocess.Popen(('grep', '-i', self.__baseName), stdin=ps.stdout, stdout=subprocess.PIPE)
            grep2 = subprocess.Popen(('grep', '-v', str(self.__myPID)), stdin=grep1.stdout, stdout=subprocess.PIPE)
            grep3 = subprocess.Popen(('grep', '-v', '/bin/sh'), stdin=grep2.stdout, stdout=subprocess.PIPE)

            if extra_grep_string:
                grep_extra = subprocess.Popen(extra_grep_string, stdin=grep3.stdout, stdout=subprocess.PIPE)
            else:
                grep_extra = grep3

            awk = subprocess.Popen(('awk', '{ print $2 }'), stdin=grep_extra.stdout, stdout=subprocess.PIPE)
            out = awk.communicate()[0]

            if not out:
                self.__write_lock_file(out)
            elif out != self.__myPID:
                print "[ERROR] " + self.__myFullFileNameWithPath + " is already running check #2 - grep: " + self.__lockFile
                print "Writing lock file and exiting..."
                f = open(self.__lockFile, 'w')
                f.write(str(out))
                f.close()
                sys.exit(1)
            else:
                self.__write_lock_file(self.__myPID)

            return True
        except Exception as e:
            print "[ERROR] Caught exception: " + str(e)
            sys.exit(1)

    def delete_lock_file(self):
        try:
            os.remove(self.__lockFile)
        except Exception as e:
            print 'Error removing lock file: ' + str(e)
            pass

    def __write_lock_file(self, pid):
        """
        This method will write the lock file with the pid of the singularly running process.
        :param pid: int
        :return: bool
        """
        try:
            f = open(self.__lockFile, 'w')
            f.write(str(pid))
            f.close()
            return True
        except Exception as e:
            print "[ERROR] Caught exception writing lock file: " + str(e)
            sys.exit(1)