import os.path, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from lib.Exceptions import *

class FileShredder(object):
    """ This class will shred a file in order to securely delete it.
    Attributes:
        file_to_shred: The path to the file to shred.
        shred_successful: Boolean of whether or not the shredding of the file occurred successfully
    """

    def __init__(self, file_to_shred):
        """ This method will construct the FileShredder class, attempt to shred the file, and return boolean result.
        :param file_to_shred: string
        :return: bool
        """
        try:
            self.shred_successful = False

            file_validator = FileExistsValidator(True)
            if not (file_validator.validate(file_to_shred)):
                self.shred_successful = True
            else:
                self.file_to_shred = file_to_shred

                shred_output = os.popen("shred -n 5 -u -z " + self.file_to_shred).read()
                if str(shred_output).strip() != '':
                    raise FileShredderException('Failed to properly shred (delete) the following file as a secure delete routine: ' + self.file_to_shred)

                self.shred_successful = True
        except Exception as e:
            print '[EXCEPTION] Shredding file (' + self.file_to_shred + ') failed: ' + str(e)