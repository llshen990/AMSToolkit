import getpass
import glob
import os
import socket
import subprocess
import re
import datetime
import random
import tempfile

from collections import OrderedDict

from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Config import AMSJibbixOptions
from Toolkit.Exceptions import AMSEncryptionException
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase

# gpg = "gpg2"
gpg = "gpg"


class AMSGpgModel(AbstractAMSBase):
    """
    A wrapper around linux PGP utility, gpg2, OpenPGP encryption and signing tool.

    The wrapper utilized information in the config.json to retrieve information such as:
        - runuser
        - directories such as incoming_dir, outgoing_dir, archive dir if needed
    """

    def __init__(self, ams_config, recurse=True):

        AbstractAMSBase.__init__(self, ams_config)

        self.gpg_user_id = self._get_gpg_user_id()
        self.recurse = recurse
        self._locate_gpg()

    def _locate_gpg(self):
        """
        Locates PGP command, which is stored in the variable `gpg`.
        Exists with return code 1, when the PGP command utility is not found.

        """
        try:
            # make sure the gpg command exists
            subprocess.check_call(["which", gpg])
            self._action_expirations()
        except subprocess.CalledProcessError:
            self.AMSLogger.error(
                "Process exited. program {program} is not found.".format(
                    empty_line=os.linesep, program=gpg
                )
            )
            raise AMSEncryptionException("Program {program} is not found. Exiting.".format(
                    empty_line=os.linesep, program=gpg))

    def import_keys(self, key_file):
        """
        Adds the given keys to the keyring.

        :param key_file: full file path of a single file to import from
        :return:
        :raises OSError when `key_file` cannot be found
        """
        assert key_file not in (None, ""), "Invalid key_file: key_file is {}.".format(
            key_file
        )

        if not os.path.exists(key_file):
            raise OSError("Failed to import PGP keys from file {}, because it does not exist.".format(key_file))

        options = OrderedDict([
            ("--batch", ""),
            ("--import", key_file)
        ])

        try:
            self.AMSLogger.info("Start to import keys from {}".format(key_file))

            self._run_command(command=gpg, options=options)

            self.AMSLogger.info("Successfully imported keys from {}".format(key_file))
        except subprocess.CalledProcessError as e:
            self.AMSLogger.error(
                "return code: {}, output: {}".format(e.returncode, e.output)
            )
            raise AMSEncryptionException('Failed to import keys from file {}.'.format(key_file))

    def export_public_keys(self, key_file):
        """
        Export all public keys of the user who is executing this program at runtime,
         and save the ASCII armored output to `key_file` that is specified in the param.

        :param key_file: path of single file to store the ASCII armored output
        :return:
        """
        assert key_file not in (None, ""), "Invalid key_file: key_file is {}.".format(
            key_file
        )
        options = OrderedDict(
            [
                # ("--no-tty", ""),
                ("--armor", ""),
                ("--export", ""),
                ("--output", key_file)
            ]
        )

        try:
            self.AMSLogger.info("Start to export public key to {}".format(os.path.join(os.getcwd(), key_file)))

            # export public key
            self._run_command(command=gpg, options=options)

            self.AMSLogger.info("Successfully exported public key to {}".format(os.path.join(os.getcwd(), key_file)))
        except subprocess.CalledProcessError as e:
            self.AMSLogger.error(
                "return code: {}, output: {}".format(e.returncode, e.output)
            )
            raise AMSEncryptionException('Failed to exporting public key to file {}.'.format(os.path.join(os.getcwd(), key_file)))

    def export_secret_keys(self, key_file, passphrase_file=None):
        """
        Export secret keys as armored ASCII text to key_file.

        :param key_file: path of single file to store the ASCII armored output
        :param passphrase_file: Passphrase-file tied to the PGP secret key. This passphrase-file should be passed as arg
        :return:
        """
        tmp_umask = os.umask(0077)
        assert key_file not in (None, ""), "Invalid key_file: key_file is {}.".format(
            key_file
        )
        options = [
                      ("--export-secret-key", ""),
                      ("--no-tty", ""),
                      ("--armor", ""),
                      ("--batch", ""),
                      ("--output", key_file)
                  ]

        try:
            self.AMSLogger.info("Start to export private key to {}".format(key_file))
            # export secret key
            self._run_command(
                command=gpg,
                options=OrderedDict(options)
            )
            self.AMSLogger.info("Successfully exported private key to {}".format(os.path.join(os.getcwd(), key_file)))

        except subprocess.CalledProcessError as e:
            self.AMSLogger.warning('Attempted export without passphrase-file, now attempting with. More recent versions'
                                   ' of gpg require passphrase/file for export but the documentation and change log '
                                   'does not clarify.')
            try:
                options.insert(-1, ("--passphrase-file", passphrase_file))
                options.insert(-1, ("--pinentry-mode", "loopback"))
                self._run_command(
                    command=gpg,
                    options=OrderedDict(options)
                )
                self.AMSLogger.info("Successfully exported private key to {}".format(os.path.join(os.getcwd(), key_file)))
            except subprocess.CalledProcessError as e:
                self.AMSLogger.error(
                    "return code: {}, output: {}".format(e.returncode, e.output)
                )
                raise AMSEncryptionException('Failed to export private key to file check if passphrase-file is '
                                             'required/valid {}.'.format(os.path.join(os.getcwd(), key_file)))
        finally:
            os.umask(tmp_umask)

    def encrypt_directories(self, recipient, directories):
        """
        Encrypts all files inside of directories, can be a single directory or a list of directories.
        """
        # get full path of all files in the directories
        files = self._list_all_files_in_directories(directories, 'encrypt')

        file_list = self.encrypt_files(recipient, files)
        if len(file_list) > 0:
            self.AMSLogger.info("Successfully encrypted files in folders: {}".format(", ".join(directories)))
        else:
            self.AMSLogger.info('No files found in {} to encrypt.'.format(', '.join(directories)))
        return file_list

    def _list_all_files_in_directories(self, directories, direction=None):
        """
        List all regular files in directories
        :param directories: a single directory or a list of directories
        :return: A list of full path of all files in directories
        """
        assert directories not in (
            None,
            (),
            [],
        ), "Argument directories is missing: directories is {}.".format(directories)

        # handles single file appropriately
        if isinstance(directories, str):
            directories = (directories,)

        files = []
        for dir_ in directories:
            for f in glob.glob(os.path.join(dir_, '*')):
                if os.path.isfile(f):
                    x = re.search('\.gpg$', f)
                    if (direction == 'encrypt' and x is None) or (direction == 'decrypt' and x):
                        files.append(f)
                elif self.recurse and os.path.isdir(f):
                    files += self._list_all_files_in_directories(f, direction)
        return files

    def encrypt(self, recipient, paths, delete):
        file_list = []
        for path in paths:
            if os.path.isdir(path):
                file_list += self.encrypt_directories(recipient, [path])
            if os.path.isfile(path):
                file_list += self.encrypt_files(recipient, path)
        if delete:
            self._delete_files(file_list)

    def encrypt_files(self, recipient, files):
        """
        Encrypts a single file or a list of files.

        :param files: a single file or a list/tuple of files. Files has to be specified.
        :param passphrase_file: passphrase file to use
        :param recipient: Recipient for encrypted files
        :raises AssertionError when files is empty.
        """
        assert recipient not in (
            None,
            "",
        ), "Invalid recipient: recipient is {}.".format(recipient)

        # handles single file appropriately
        if isinstance(files, str):
            files = (files,)
        elif len(files) == 0:
            return files

        try:
            self.AMSLogger.info(
                "Starting to encrypt for user: {}".format(recipient)
            )
            self.AMSLogger.info("Starting to encrypt the following files: {}".format(files))

            # the order of the options matter to the pgp utility, if --encrypt-file is passed first,
            # encryption will fail.
            options = OrderedDict(
                [
                    ("-r", recipient),
                    ("--trust-model", "always"),
                    ("--no-secmem-warning", ""),
                    ("--batch", ""),
                    ("--yes", ""),
                    ("--encrypt-file", '{}'.format(' '.join(['"{}"'.format(in_file) for in_file in files]))),
                ]
            )

            self._run_command(command=gpg, options=options)

            return files
        except subprocess.CalledProcessError as e:
            self.AMSLogger.error(
                "return code: {}, output: {}".format(e.returncode, e.output)
            )
            raise AMSEncryptionException('Failed to encrypt files: {}.'.format(files))

    def decrypt(self, passphrase_file, paths, delete):
        file_list = []
        for path in paths:
            if os.path.isdir(path):
                file_list += self.decrypt_directories(passphrase_file, [path])
            if os.path.isfile(path):
                file_list += self.decrypt_files(passphrase_file, path)
        if delete:
            self._delete_files(file_list)

    def _delete_files(self, file_list):
        try:
            self.AMSLogger.info('Removing original files.')
            for stale_file in file_list:
                os.remove(stale_file)
        except Exception as e:
            self.AMSLogger.error('Unable to remove original files.{}'.format())

    def decrypt_directories(self, passphrase_file, directories):
        """
        Decrypts regular files in a single directory or a list of directories.
        :param passphrase_file: PGP passphrase file.
        :param directories: a single file or a list/tuple of files. Files has to be specified.
        :raises AssertionError when passphrase is empty or files is empty.
        """
        files = self._list_all_files_in_directories(directories, 'decrypt')
        file_list = self.decrypt_files(passphrase_file, files)
        if len(file_list) > 0:
            self.AMSLogger.info("Successfully decrypted files in folders: {}".format(", ".join(directories)))
        else:
            self.AMSLogger.info('No files found in {} to decrypt.'.format(', '.join(directories)))
        return file_list

    def decrypt_files(self, passphrase_file, files):
        """
        Decrypts a single file or a list of file using passphrase
        :param passphrase_file: PGP passphrase file. It cannot be empty.
        :param files: a single file or a list of files to be decrypted.
        :raises AssertionError when passphrase is empty or files is empty.
        """
        assert passphrase_file not in (
            None,
            "",
        ), "Invalid passphrase: passphrase is {}.".format(passphrase_file)

        # handles single file appropriately
        if isinstance(files, str):
            files = (files,)
        elif len(files) == 0:
            return files

        try:
            self.AMSLogger.info("Starting to decrypt the following files: {}".format(files))

            options = [
                ("--trust-model", "always"),
                ("--no-secmem-warning", ""),
                ("--batch", ""),
                ("--yes", ""),
                ("--passphrase-file", passphrase_file),
                ("--decrypt-file", '{}'.format(' '.join(['"{}"'.format(in_file) for in_file in files])))
            ]

            self._run_command(command=gpg, options=OrderedDict(options))

            return files
        except subprocess.CalledProcessError as e:
            self.AMSLogger.warning("Attempted to decrypt files without pinentry-mode specified.")
            try:
                options.insert(-1, ("--pinentry-mode", "loopback"))
                self._run_command(
                    command=gpg,
                    options=OrderedDict(options)
                )
                self.AMSLogger.info("Decrypted files with pinentry-mode specified")
                return files
            except subprocess.CalledProcessError as e:
                self.AMSLogger.error(
                    "return code: {}, output: {}".format(e.returncode, e.output)
                )
                raise AMSEncryptionException('Failed to decrypt files: [{}]'.format(files))

    def generate_keys(self, params_file=None, name=None, email=None, passphrase=None, key_type='RSA', key_length=4096, expire=0):
        """
        Generates a new PGP key pair.
        """
        handle = None
        chars = None
        if params_file is None:
            if passphrase is None:
                chars = [x for x in range(33, 92) + range(93, 127)]  # No pesky backslashes please
                rnd = random.SystemRandom()
                passphrase = ''.join(chr(rnd.choice(chars)) for _ in range(20))

            name = getpass.getuser() if name is None else name
            email = '{}@wnt.sas.com'.format(name) if email is None else email

            (handle, params_file) = tempfile.mkstemp(prefix='params_')
            with open(params_file, 'w+') as param_handle:
                params = os.linesep.join(['Key-Type: {}'.format(key_type),
                                          'Key-Length: {}'.format(key_length),
                                          'Subkey-Type: {}'.format(key_type),
                                          'Subkey-Length: {}'.format(key_length),
                                          'Name-Real: {}'.format(name),
                                          'Name-Comment: pgp keys for {}'.format(name),
                                          'Name-Email: {}'.format(email),
                                          'Expire-Date: {}'.format(expire),
                                          'Passphrase: {}'.format(passphrase),
                                          ''])
                param_handle.write(params)

        try:
            command = '--generate-key'
            while True:
                try:
                    # run key generation
                    proc = subprocess.Popen(
                        [gpg, "--batch", command, params_file],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    outs, errs = proc.communicate()
                    # command line output is channeled to errs
                    for err in errs.split("\n"):
                        if err.startswith("gpg: key") and err.endswith("marked as ultimately trusted"):
                            # gpg key id is the third word in the phrase
                            key_id = err.split()[2]
                            self.AMSLogger.info('Generated key_id: {}'.format(key_id))
                            return key_id
                        elif re.search('No such file or directory', err):
                            self.AMSLogger.error('Parameter file: {} was not found.'.format(params_file))

                    raise #AMSEncryptionException('Error encountered generating pgp key.')
                except Exception as e:
                    if command == '--gen-key':
                        self.AMSLogger.error('Failed to generate key with either --gen-key or --generate-key. '
                                             'Raised error may mask original error.')
                        raise e
                    self.AMSLogger.warning('Generate failed with {} which is probably just indicative of gpg version.'
                                           .format(command))
                    command = '--gen-key'

        except OSError as error:
            self.AMSLogger.error(error)
            raise AMSEncryptionException("Failed to generate keys in batch mode.")
        except ValueError as error:
            self.AMSLogger.error(error)
            raise AMSEncryptionException("Failed to generate keys in batch mode.")
        except TypeError:
            self.AMSLogger.error('Check the format of the parameters file: {}'.format(params_file))
        finally:
            if chars is not None:
                self.AMSLogger.info('Not removing temporary parameters file as it contains only copy of passphrase. {}'.format(
                    params_file
                ))
            elif handle is not None and os.path.exists(params_file):
                self.AMSLogger.info('Removing temporary parameters file.')
                os.remove(params_file)

    @staticmethod
    def delete_keys(key_id):
        """Delete both public key and secret key identified by key_id"""
        assert key_id not in ("", None), "Invalid key_id: {}".format(key_id)

        fingerprint = AMSGpgModel.get_fingerprint(key_id)
        # delete secret key first
        subprocess.check_output(
            [gpg, "--batch", "--yes", "--delete-secret-key", fingerprint]
        )
        # delete public key
        subprocess.check_output([gpg, "--batch", "--yes", "--delete-key", fingerprint])

    @staticmethod
    def get_fingerprint(key_id):
        assert key_id not in ("", None), "Invalid key_id: {}".format(key_id)
        # get fingerprint from key id
        proc = subprocess.Popen(
            [gpg, "--list-secret-key", "--with-colon", "--fingerprint", key_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        outs, errs = proc.communicate()

        for line in outs.split("\n"):
            if line.startswith("fpr"):
                words = line.split(":")
                # fingerprint string is the second from the last
                return words[-2]

    def _run_command(self, command, options, mask_options=OrderedDict({})):
        """
        Reconstructs the shell command to be run. Masks sensitive information such as passphrases listed in the mask_options dictionary.
        """

        def _str_masked(_options):
            return " ".join(["{} *****".format(k) for k in _options.keys()])

        def _str(_options):
            return " ".join(["{} {}".format(k, v) for k, v in _options.items()])

        options_string = _str(options)
        mask_options_string = _str(mask_options)
        self.AMSLogger.debug(
            "start to run command as {user}: {command} {options} {mask_options}".format(
                user=getpass.getuser(),
                command=command,
                options=options_string,
                mask_options=_str_masked(mask_options),
            )
        )
        result = subprocess.check_output(
            "{} {} {}".format(command, options_string, mask_options_string), stderr=subprocess.STDOUT, shell=True
        )
        self.AMSLogger.debug(result)
        return result

    def _get_gpg_user_id(self):
        """
        Get PGP user id.

        This id is used during encryption and decryption.

        :return: a string such as tlarun@vsp.sas.com
        """

        if self.AMSConfig.run_user:
            run_user = self.AMSConfig.run_user
        else:
            run_user = getpass.getuser()

        return "{user}@{domain}".format(
            user=run_user, domain=socket.getfqdn().split(".", 1)[-1]
        )

    def check_expirations(self, threshold=7):
        keys = self._run_command(gpg, {'--list-keys': '', '--with-colon': ''}).strip().split('\n') +\
               self._run_command(gpg, {'--list-secret-keys': '', '--with-colon': ''}).strip().split('\n')
        exp = []
        for key in keys:
            line = key.split(':')
            if len(line) > 6 and (line[5] and line[6]):
                key_type = ''
                if line[0] == 'pub':
                    key_type = 'Public key'
                # Subkey can simply be removed from this matching if deemed unnecessary or duplicative
                elif line[0] == 'sub':
                    key_type = 'Subkey'
                elif line[0] == 'sec':
                    key_type = 'Secret key'

                try:
                    delta = datetime.datetime.fromtimestamp(int(line[6])) - datetime.datetime.fromtimestamp(int(line[5]))
                    if key_type and delta.days <= threshold:
                        exp.append((key_type, line[4], delta.days))
                except Exception as e:
                    self.AMSLogger.error('Unexpected format for PGP key\n{}'.format(str(e)))
        return exp

    def _action_expirations(self):
        expiring_keys = self.check_expirations()
        if len(expiring_keys) > 0:
            jibbix_options = AMSJibbixOptions()
            jibbix_options.comment_only = 'yes'
            jibbix_options.link = 'comm'
            try:
                jibbix_options.project = self.AMSConfig.AMSEnvironments[0]['tla']
            except:
                jibbix_options.project = 'SSO'
            zabbix = AMSZabbix(self.AMSLogger)
            try:
                zabbix.zabbix_proxy = self.AMSConfig['zabbix_proxy']
            except:
                zabbix.zabbix_proxy = self.AMSDefaults.zabbix_proxy

            message = []
            for (key_type, signature, days) in expiring_keys:
                line = 'PGP {} with signature: {} will expire in {} days.'.format(key_type, signature, days)
                self.AMSLogger.warning(line)
                message.append(line)

            self.AMSLogger.info('Sending expired keys to zabbix')
            result = zabbix.call_zabbix_sender(self.AMSDefaults.default_zabbix_key_no_schedule,
                                               '{}\n{}'.format(jibbix_options.str_from_options(), '\n'.join(message)))
            if not result:
                self.AMSLogger.error('Unable to update zabbix with expiring PGP keys.')



