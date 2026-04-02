from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from builtins import str, chr, object
import base64


class AMSCrypto(object):
    def __init__(self):
        pass

    @staticmethod
    def pad(s):
        bs = 16
        return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)

    @staticmethod
    def unpad(s):
        try:  # py2
            return str(s[0:-ord(s[-1])])
        except:  # py3
            return s[0:-s[-1]]

    @staticmethod
    def encrypt(secret, str_to_encrypt):
        str_to_encrypt = AMSCrypto.pad(str_to_encrypt)
        cipher = Cipher(algorithms.AES(secret), modes.ECB(), backend=default_backend())
        encryptor = cipher.encryptor()
        try:
            encrypted = base64.b64encode(encryptor.update(bytes(str(str_to_encrypt, 'utf8'))) + encryptor.finalize())
        except TypeError:
            encrypted = base64.b64encode(encryptor.update(bytes(str_to_encrypt, 'utf8')) + encryptor.finalize())
        return encrypted

    @staticmethod
    def decrypt(secret, encrypted_str):
        cipher = Cipher(algorithms.AES(secret), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        return AMSCrypto.unpad(decryptor.update(base64.b64decode(encrypted_str)) + decryptor.finalize())
