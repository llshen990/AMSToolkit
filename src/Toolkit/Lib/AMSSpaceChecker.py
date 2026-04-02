import os
import os.path
# import fnmatch
import logging
import sys

from datetime import date,datetime,timedelta
from Toolkit.Lib import AMSLogger

class AMSSpaceChecker():

    def __init__(self,file_system):
        self.AMSLogger = AMSLogger(self.__whoami())
        self.filesystem = file_system
        self.m_days = 1 ## modified in m_days days
        self.files = [] ## All files found in that fle system
        self.dirlist = [] ## All directories found in that file system
        self.m_files = [] ## The files list that were modified in m_days days
        self.m_dirlist = [] ## The dir list that were modified in m_days days
        self.m_dirset=set()  ## A set which collects files that have been modified recently


    def _dirsize(self,dir):
        if not os.path.isdir(dir):
            self.AMSLogger.debug(dir + " is not a directory")
            return 0
        try:
            size = sum(
                os.path.getsize(os.path.join(dir, f)) for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f)))
        except(OSError, IOError):
            self.AMSLogger.debug("Unable to get the size of directory "+ dir)
            return None
        return size


    def find_dirs_and_files(self,root, m_days, exclude_dirs):

        if root is None:
            root = self.filesystem

        if not m_days:
            self.m_days = 1
        else:
            self.m_days = m_days
        dt = datetime.now() - timedelta(hours=24*self.m_days)
        # print "Files or directories that have been modified since "+ str(dt)
        self.AMSLogger.info("Files or directories that have been modified since "+ str(dt))

        for root, dirnames, filenames in os.walk(root):

            for d in exclude_dirs:
                if d in dirnames:
                    dirnames.remove(d)
            for filename in filenames:
                try:
                    file_stat = os.stat(os.path.join(root, filename))
                    self.files.append(os.path.join(root, filename))  ## get the files[]
                    if datetime.fromtimestamp(file_stat.st_mtime(os.path.join(root, filename))) > dt:
                        self.m_files.append(os.path.join(root, filename))   ## get the m_files[]
                        self.m_dirset.add(root)
                except:
                    self.AMSLogger.debug('Warning: ' + os.path.join(root, filename) + ' is not a valid file.Skipping..')
                    continue
                # files.append(os.path.join(root, filename))

            for d in dirnames:
                try:
                    os.stat(os.path.join(root, d))
                    self.dirlist.append(os.path.join(root, d))   ## get the dirlist[]
                    # if datetime.fromtimestamp(os.path.getmtime(os.path.join(root,d))) > dt:
                    #     m_dirlist.append(os.path.join(root,d))
                except:
                    self.AMSLogger.debug('Warning: ' + os.path.join(root, d) + ' is not a valid directory. Skipping...')
                    continue
        self.m_dirlist=list(self.m_dirset)


    def get_large_files(self,filelist,n):
        out_list=[]
        if not n:
            n = 25
        files_dict = {}
        for name in filelist:
            files_dict[name] = os.path.getsize(name)
        result = sorted(files_dict.items(), key=lambda d: d[1], reverse=True)[:n]
        for i, t in enumerate(result, 1):
            # print i, t[0], t[1]
            my_list=[i,t[0],self.GetHumanReadable(t[1],precision=2)]
            out_list.append(my_list)
        return out_list


    def get_large_dirs(self,dirlist,n):
        out_list=[]
        if not n:
            n = 10
        dirs_dict = {}
        for d in dirlist:
            dirs_dict[d] = self._dirsize(d)
        result1 = sorted(dirs_dict.items(), key=lambda d: d[1], reverse=True)[:n]
        for i, t in enumerate(result1, 1):
            if t[1] is None:
                continue
            my_list = [i, t[0], self.GetHumanReadable(t[1],precision=2)]
            out_list.append(my_list)
        return out_list

    def GetHumanReadable(self, size, precision=2):
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        suffixIndex = 0
        while size > 1024 and suffixIndex < len(suffixes):
            suffixIndex += 1  # increment the index of the suffix
            size = size / 1024.0  # apply the division
        return "%.*f %s" % (precision, size, suffixes[suffixIndex])

    def __whoami(self):
        return sys._getframe(1).f_code.co_name








