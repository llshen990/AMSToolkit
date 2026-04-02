import os.path, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from lib.Helpers import FileGetTransFilename, FileGetTransDate, DecryptPgP

class EmptyFileDependency(object):
    """ This class will handle checking other files to see if they are empty. If all other files are empty in the related_files list, then
     the calling file can also be empty.
    """

    def __init__(self, file_name, related_files, decrypt_script_path, my_file_size):
        """
        Initializes EmptyFileDependency class
        Args:
            file_name: string - 'my' filename.
            related_files: list - list of related files that also have to be empty
            decrypt_script_path: string - path to decrypt script
            my_file_size: string - size of the file currently in validation
        """

        # print '[DEBUG] file_name: %s' % file_name
        # print '[DEBUG] related_files: %s' % related_files
        # print '[DEBUG] decrypt_script_path: %s' % decrypt_script_path
        # print '[DEBUG] my_file_size: %s' % my_file_size

        self.file_name = file_name
        self.related_files_list_raw = related_files
        self.decrypt_script_path = str(decrypt_script_path).strip()
        self.file_size = my_file_size
        self.found_file_not_empty = ''

        file_exists_validator = FileExistsValidator(True)
        if not file_exists_validator.validate(self.file_name):
            raise Exception('File: ' + self.file_name + ' does not exist')

        if not self.related_files_list_raw or (len(self.related_files_list_raw) < 1):
            raise Exception('No related files to validate for content have been passed.')

        self.related_files = []
        for related_file in self.related_files_list_raw:
            related_file = related_file.strip()
            if related_file:
                self.related_files.append(related_file)

        if not self.related_files_list_raw or (len(self.related_files_list_raw) < 1):
            raise Exception('No related files to validate for content have been passed - empty files were passed')

    def validate(self):
        """
        This method will validate if a file is allowed to be empty.  All 'related files' must also be empty
        to validate.
        Returns: bool
        """

        if self.file_size > 0:
            return True

        file_exists_validator = FileExistsValidator(True)
        get_trans_filename = FileGetTransFilename()
        file_get_date = FileGetTransDate()
        tran_date_tmp = file_get_date.get_trans_date_from_filename(self.file_name)
        tran_date = tran_date_tmp.strftime('%Y%m%d')
        allowed_to_be_empty = True
        for related_file_type in self.related_files:
            # print "related_file_type: " + str(related_file_type)
            # print "tran_date: " + str(tran_date)
            try:
                filename = get_trans_filename.get_file_name_from_type(related_file_type, tran_date)
            except Exception as e:
                print 'Exception in get_trans_filename.get_file_name_from_type: ' + str(e)
                raise
            # print "file: " + str(filename)
            if not file_exists_validator.validate(filename):
                raise Exception(filename + ' does not exist')
            decrypt_pgp = DecryptPgP(filename, self.decrypt_script_path)

            file_size = os.path.getsize(decrypt_pgp.decrypted_file_path)
            if file_size > 0:
                allowed_to_be_empty = False
                self.found_file_not_empty = filename + ' --> ' + str(file_size) + ' bytes'
                break

        if not allowed_to_be_empty and self.file_size == 0:
            raise Exception('This file is empty and can NOT be because a corresponding file is NOT empty: ' + self.found_file_not_empty)

        return True
