import hashlib


class Md5Sum(object):
    """ This class will facilitate md5 hashing methods and helpers.
    """

    def __init__(self):
        """ This method will construct the Md5Sum class:
        :return Md5Sum
        """

    def md5_hash_for_file(self, file_path):
        """ This method will calculate the md5
        :param file_path: str
        :return: str
        """
        return hashlib.md5(open(file_path, 'rb').read()).hexdigest()

    def compare_hash_for_files(self, file_path1, file_path_2):
        """ This method will determine if the *file_path1* has the same contents as *file_path_2*
        :param file_path1: str
        :param file_path_2: str
        :return: bool
        """
        return hashlib.md5(open(file_path1, 'rb').read()).hexdigest() == hashlib.md5(open(file_path_2, 'rb').read()).hexdigest()

    def compare_hash_for_landing_and_validated_files(self, landing_file, validated_file):
        """
        :param landing_file: str
        :param validated_file: str
        :return: bool
        """
        return hashlib.md5(open(landing_file, 'rb').read()).hexdigest() == open(validated_file, 'rb').read()

    def create_validated_md5_file(self, landing_file, validated_file_path):
        """ This method will create the validated file and put the md5() hash of the landing file inside it.
        :param landing_file: str
        :param validated_file_path: str
        :return: bool
        """
        fo = open(validated_file_path, "wb")
        fo.write(self.md5_hash_for_file(landing_file))
        fo.close()
        return True
