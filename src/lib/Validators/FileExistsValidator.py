# @author owhoyt
import os.path
from AbstractValidator import AbstractValidator

class FileExistsValidator(AbstractValidator):
    """This class validates a file to ensure that it exists and is readable"""

    def __init__(self, debug=False):
        """ Instantiates an FileExistsValidator object
        :param debug: bool
        :return: FileExistsValidator
        """
        AbstractValidator.__init__(self, debug)

    def validate(self, data_input, options=None):
        """Validates *data_input* to ensure that it is a valid URL w/o checking existence.
        :type data_input: str
        :param data_input: Input to validate
        :param options: not supported for this validation type.
        :return: bool
        """
        try:
            file_error = False
            if not os.path.isfile(data_input):
                self.add_error(str(data_input), 'Input file does not exist.  Please check your path and try again.')
                file_error = True
            elif not os.access(data_input, os.R_OK):
                self.add_error(str(data_input), 'Input file exists, but is not readable.  Please check permissions and try again.')
                file_error = True

            if file_error:
                return False
            else:
                return True

        except Exception as e:
            self.add_error(str(e), "Exception when validating File")
            return False

    @staticmethod
    def is_readable(fpath):
        """
        Will return true if file is readable.
        :param fpath: path to script.
        :type fpath: str
        :return: returns True if the script has the read prop set.
        :rtype: bool
        """
        return os.path.isfile(fpath) and os.access(fpath, os.R_OK)

    @staticmethod
    def is_writeable(fpath):
        """
        Will return true if file is writeable.
        :param fpath: path to script.
        :type fpath: str
        :return: returns True if the script has the write prop set.
        :rtype: bool
        """
        return os.path.isfile(fpath) and os.access(fpath, os.W_OK)

    @staticmethod
    def is_exe(fpath):
        """
        Will return true if file is executable.
        :param fpath: path to script.
        :type fpath: str
        :return: returns True if the script has the executable prop set.
        :rtype: bool
        """
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    @staticmethod
    def is_dir(fpath):
        """
        Will return true if file is a directory.
        :param fpath: path to script.
        :type fpath: str
        :return: returns True if the file is a directory.
        :rtype: bool
        """
        return os.path.isdir(fpath)

    @staticmethod
    def directory_readable(directory_path):
        """
        Will return true if directory is present and readable.
        :param directory_path: path to directory.
        :type directory_path: str
        :return: returns True if the directory is available and readable
        :rtype: bool
        """
        return os.path.isdir(directory_path) and os.access(directory_path, os.R_OK)

    @staticmethod
    def directory_writeable(directory_path):
        """
        Will return true if directory is present and writeable.
        :param directory_path: path to directory.
        :type directory_path: str
        :return: returns True if the directory is available and writeable
        :rtype: bool
        """
        return FileExistsValidator.directory_readable(directory_path) and os.access(directory_path, os.W_OK)

    @staticmethod
    def directory_executable(directory_path):
        """
        Will return true if directory is present and executable.
        :param directory_path: path to directory.
        :type directory_path: str
        :return: returns True if the directory is available and executable
        :rtype: bool
        """
        return FileExistsValidator.directory_readable(directory_path) and os.access(directory_path, os.X_OK)

    @staticmethod
    def directory_exists(directory_path):
        """
        Will return true if directory is present.
        :param directory_path: path to directory.
        :type directory_path: str
        :return: returns True if the directory is available
        :rtype: bool
        """
        return os.path.exists(directory_path)