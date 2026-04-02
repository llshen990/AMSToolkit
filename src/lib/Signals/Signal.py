import ConfigParser
import io
import os.path
import sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Exceptions import SignalException
from lib.Validators import PresenceOfValidator, FileExistsValidator

class Signal(object):
    """
    Signal houses all functionality with respect to managing signal files for automation.
        presence_of_validator: PresenceOfValidator.
        file_exists_validator: FileExistsValidator.
        signal_path: Directory where the signal will reside.
        signal_name: Filename of the signal.
        config: ConfigParser.
        signal_data: Data in the signal.
        full_file_path: Full path to the signal file.
    """

    def __init__(self, directory_path, signal_name, load_signal=False, default_extension='.sig', replace_extension=True):
        """
        Inits the Signal object.
        :param directory_path: Directory that the signal resides in.
        :type directory_path: str
        :param signal_name: Filename of signal.
        :type signal_name: str
        :param load_signal: Whether or not to try and load the signal from an existing signal file.
        :type load_signal: bool
        :param replace_extension: True will not replace the original extension with the default extension
        :type replace_extension: bool
        """
        self.presence_of_validator = PresenceOfValidator(True)
        self.file_exists_validator = FileExistsValidator(True)
        default_extension = str(default_extension).strip()
        if default_extension == '':
            raise SignalException('Signal extension required!')

        self.default_extension = default_extension

        # full path to the signal directory
        self.signal_path = str(directory_path).strip()
        if not self.presence_of_validator.validate(self.signal_path, 'signal_path'):
            raise SignalException('Signal directory path required.')

        # signal filename
        self.signal_name = str(signal_name).strip()
        if not self.presence_of_validator.validate(self.signal_name, 'signal_name'):
            raise SignalException('Signal name required.')

        self._clean_sig_name(replace_extension)

        # get config options
        self.config = ConfigParser.ConfigParser()
        self.config.read(APP_PATH + '/Config/ssod_validator.cfg')

        # data (text) to save into the file of the signal (optional)
        self.signal_data = None

        # full file path
        self.full_file_path = os.path.normpath(self.signal_path + os.path.sep + self.signal_name)

        # do we want to load the signal during init?
        if load_signal:
            self.load_signal(self.full_file_path)

        # make the signal directory if it doesn't already exist
        if not os.path.exists(self.signal_path):
            os.makedirs(self.signal_path)

    def _clean_sig_name(self, replace_extension):
        """
        This method is meant to be called internally and will standardize the signal name to have a .sig extension
        :param replace_extension: True will not replace the original extension with the default extension
        :type replace_extension: bool
        :return: Signal name cleaned
        :rtype: string
        """
        if replace_extension:
            sig_extension = os.path.splitext(self.signal_name)[-1]
            self.signal_name = self.signal_name.replace(sig_extension, '') + self.default_extension
        else:
            self.signal_name = self.signal_name + self.default_extension
        return self.signal_name

    def load_signal(self, full_signal_path):
        """
        This method will load the Signal object based on the full path to an existing file.
        :param full_signal_path: Full path to signal file.
        :type full_signal_path: str
        :return: True upon success.  False if signal doesn't exist
        :rtype: bool
        """
        try:
            full_signal_path = str(full_signal_path).strip()
            if not self.presence_of_validator.validate(full_signal_path, 'full_signal_path'):
                raise SignalException('Full path to signal file required.')

            self.full_file_path = full_signal_path
            self.signal_path = os.path.dirname(self.full_file_path)
            self.signal_name = os.path.basename(self.full_file_path)

            if self.file_exists_validator.validate(full_signal_path):
                self.get_signal_data()

            return True
        except Exception as e:
            raise SignalException(str(e))

    def write_signal_and_data(self, replace_data=None):
        """
        This method will create the signal file and data passed in via the replace_data command.
        :param replace_data: Data to write into the signal file.
        :type replace_data: str
        :return: True upon success.
        :rtype: bool
        """
        try:
            replace_data = str(replace_data).strip()
            self.signal_data = '' if replace_data == '' or None else replace_data

            with io.FileIO(self.full_file_path, "w") as fp:
                fp.write(self.signal_data)

            return True

        except Exception as e:
            raise SignalException('Could not write signal and data: ' + str(e))

    def append_signal_data(self, more_data):
        """
        This method will append data to the contents of the signal file.  It will include a new line automatically.
        :param more_data: Data to be appended to the signal.
        :type more_data: str
        :return: True upon success
        :rtype: bool
        """
        try:
            more_data = str(more_data).strip()
            more_data = '' if more_data == '' or None else more_data
            if not self.presence_of_validator.validate(more_data, 'more_data'):
                return

            with io.FileIO(self.full_file_path, "a") as fp:
                fp.write(os.linesep + more_data)

            self.get_signal_data()

            return True

        except Exception as e:
            raise SignalException('Could not append signal data: ' + str(e))

    def get_signal_data(self):
        """
        This method will return the contents of the signal file.
        :return: Contents of the signal file.
        :rtype: str
        """
        try:
            with open(self.full_file_path, 'r') as fp:
                self.signal_data = fp.read()
            return self.signal_data
        except Exception as e:
            raise SignalException(str(e))

    def remove_signal(self):
        """
        Removes the signal.
        :return: Returns os.remove return.
        :rtype: bool
        """
        try:
            if not self.file_exists_validator.validate(self.full_file_path):
                return True

            os.remove(self.full_file_path)

            return True
        except Exception as e:
            raise SignalException('Could not remove signal: ' + str(e))

    def exists(self):
        """
        Checks to see if a signal file exists or not.
        :return: Returns true if signal exists or false if not.
        :rtype: bool
        """
        return self.file_exists_validator.validate(self.full_file_path)

    def get_file_and_data(self):
        """
        :return: Returns full signal path + any data written to the signal.
        :rtype: str
        """
        ret_str = self.full_file_path
        # noinspection PyBroadException
        try:
            if self.exists():
                sig_data = str(self.get_signal_data()).strip()
                if sig_data != '':
                    ret_str += ":" + os.linesep + self.get_signal_data()
        except Exception:
            pass
        finally:
            return ret_str

    @staticmethod
    def get_join_separator():
        """
        :return: Returns formatted string to use as a separator in join's.
        :rtype: str
        """
        return '----------------------' + os.linesep

    def __str__(self):
        ret_var = 'signal_path: ' + str(self.signal_path)
        ret_var += os.linesep
        ret_var += 'signal_name: ' + str(self.signal_name)
        ret_var += os.linesep
        ret_var += 'signal_data: ' + str(self.signal_data)
        ret_var += os.linesep
        ret_var += 'full_file_path: ' + str(self.full_file_path)
        return ret_var