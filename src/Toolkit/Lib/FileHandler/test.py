import os
import time
from os.path import join, islink
import scandir
from Toolkit.Lib.FileHandler import AbstractFileHandler
import fnmatch

from Toolkit.Exceptions import AMSFatalException, AMSValidationException

file_pattern = '*.pyc'
file_age=15
file_count = 4
max_depth = 5
min_depth = 1
follow_symlinks = False
level='File'
type='Compress'
directory_to_watch='/vagrant/src/Toolkit/Lib'
old_list=[]

def match(path, name):
    # print('Validating pattern=%s' % file_pattern)
    if fnmatch.fnmatch(name, file_pattern):
        # print('file=%s matches pattern=%s' % (name, file_pattern))

        if file_age is not None:
            creation_time = os.stat(path).st_mtime
            current_time = int(time.time())
            print(current_time)
            print(creation_time)
            if (current_time - creation_time) >= file_age * 60 * 60 * 24:
                # print('File is older than '+str(file_age)+' and being deleted...')
                old_list.append(path)
            elif file_count > 0:
                # print(
                    # 'file=%s does *NOT* match file age of %s days' % (name, file_age))
                return True
            else:
                return False
        else:
            return False

    # print('file=%s does *NOT* match pattern=%s' % (name, file_pattern))
    return False


def search():
    root_dir = directory_to_watch
    total=0
    # max_depth = float('inf') if self.AMSFileHandler.max_depth == -1 else self.AMSFileHandler.max_depth
    xlist = []
    # agelist=[]

    if min_depth > max_depth:
        raise AMSValidationException('No Results: Min Depth ({}) > Max Depth ({})'.format(min_depth, max_depth))

    follow_symlinks = False
    if follow_symlinks in ['Yes']:
        follow_symlinks = True

    try:
        print('Executing {} on {}'.format(type, root_dir))
        for root, dirs, files, depth in AbstractFileHandler.walk(root_dir, followlinks=follow_symlinks):

            try:
                if min_depth <= depth <= max_depth:
                    if level in ['Directory']:
                        for directory in dirs:
                            total += 1
                            path = os.path.join(root, directory)
                            if match(path, directory):
                                # self._file_handler_type(path, directory)
                                # print('Below directories are older than file_age:')
                                # print(path)
                                # print(directory)
                                xlist.append((path,directory))

                        if type in ['Compress']:
                            return

                    elif level in ['File']:
                        for file_name in files:
                            total += 1
                            try:
                                path = os.path.join(root, file_name)
                                if match(path, file_name):
                                    try:
                                        # self._file_handler_type(path, file_name)
                                        # print('Below files are older than file_age')
                                        # print(path)
                                        # print(file_name)
                                        xlist.append((path,file_name))
                                    except IOError as io:
                                        print(
                                            'File permission error encountered for {}'.format(file_name))
                                        # selErrorList.append(io)

                            except Exception as e:
                                import traceback
                                print(
                                    "Caught an exception searching file_name={}: {}".format(file_name, str(e)))
                                print("Traceback: {}".format(traceback.format_exc()))
            except Exception as e:
                import traceback
                print("Caught an exception searching: {}".format(str(e)))
                print("Traceback: {}".format(traceback.format_exc()))
        print('Total= '+str(total))
        if len(xlist) > 0:
            print('xlist...')
            print(len(xlist))
            print(xlist)
            keeplist=sorted(xlist, key=lambda f: os.stat(f[0]).st_mtime, reverse=True)[:file_count]
            xxlist = sorted(xlist, key=lambda f: os.stat(f[0]).st_mtime, reverse=True)[file_count:]
            print('keeplist')
            print(len(keeplist))
            print(keeplist)
            print('xxlist..')
            print(xxlist)
            print(len(xxlist))
            if len(xxlist) > 0:
                for item in xxlist:
                    try:
                        # self._file_handler_type(item[0], item[1])
                        print('Processing the xxlist...')
                        print(item[0])
                        # print(item[1])
                    except IOError as io:
                        print('File permission error encountered for {}'.format(item[0]))
                        # self.ErrorList.append(io)
                    except Exception as e:
                        print('Error occurred while procesing {}'.format(item[0]))
                        # self.ErrorList.append(e)

    except Exception as e:
        print(e)

search()
print('oldlist...')
print(len(old_list))
print(old_list)