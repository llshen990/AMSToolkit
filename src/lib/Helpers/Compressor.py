import os.path, sys, zipfile, subprocess

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from lib.Validators import FileExistsValidator
from lib.Exceptions import CompressionException

class Compressor(object):
    def __init__(self, input_file, temp_location='/tmp/unzip_temp'):
        self.file = input_file.strip()
        file_exists_validator = FileExistsValidator(True)
        if not file_exists_validator.validate(self.file):
            raise CompressionException('__init__: file does not exist: ' + self.file)

        self.temp_location = temp_location
        if not os.path.exists(self.temp_location):
            os.makedirs(self.temp_location)

    def unzip(self):
        zip_ref = zipfile.ZipFile(self.file, 'r')
        zip_ref.extractall(path=self.temp_location)
        zip_ref.close()

    def zip_dir(self, output_file, directory=None):
        output_file = output_file.strip()
        if not directory:
            directory = self.temp_location

        zipf = zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(directory):
            for file_to_zip in files:
                arcname_struct = os.path.basename(os.path.dirname(os.path.join(root, file_to_zip))) + '/' + file_to_zip
                zipf.write(os.path.join(root, file_to_zip), arcname=arcname_struct)
        zipf.close()

    def get_temp_path(self):
        return self.temp_location

    def delete(self):
        pm = subprocess.Popen('find ' + self.temp_location + ' -type f -exec shred -n 3 -u -z {} \;', shell=True)
        pm.wait()

    def __del__(self):
        # shred the extracted files
        self.delete()