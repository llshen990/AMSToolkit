import argparse
import sys
import traceback
import os
import re
import socket
import getpass
from os import path
from stat import *

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Config import AMSConfig, AMSEnvironment
from Toolkit.Lib import AMSLogger
from Toolkit.Models import AMSSecretServerModel, AMSGpgModel
from Toolkit.Exceptions import AMSSecretException, AMSConfigException, AMSEncryptionException
from Toolkit.Thycotic import AMSSecretServer

ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + ".log")
public_key_file = "public_key.asc"
private_key_file = "private_key.asc"


def _parse_args(args=None):
    description_text = """Description: \n
    This is a controller that handles file encryption, decryption,
    exporting and importing secrets from and to Thycotic Secret Server.
    
    Under the hood, this controller calls the linux PGP utility, gpg2, to handle file encryption, decryption, 
    exports and imports. 
    
    During imports and exports, you will be prompted to key in your personal Thycotic username and password. 
    This is because your credentials are needed in order to upload secret files into Thycotic, which will increase
    auditability in our key management process.
        
    Caveats:
        1. To export keys from tlarun user's key rings, please run this controller as tlarun user.
    
    """
    use_cases_text = """
    == PGP ==
    
    1. To encrypt all regular files in a directory or directories:
        
         /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_encryption_handler.py --config_file=<config-json-file-path> --action=encrypt --type=PGP <directory-name-1> <directory-name-2>
        
    2. To decrypt all regular files in a directory or directories:
        
         /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_encryption_handler.py --config_file=<config-json-file-path> --action=decrypt --passphrase_file <passphrase_file> --type=PGP <directory-name-1> <directory-name-2>
        
    3. To encrypt a file or files with pgp public key:
        
         /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_encryption_handler.py --config_file=<config-json-file-path> --action=encrypt --type=PGP <file-name-1> <file-name-2>

        note: The encrypted file will be placed in the same folder as the original file.

    4. To decrypt a file or files with pgp:
        
         /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_encryption_handler.py --config_file=<config-json-file-path> --action=decrypt --passphrase_file <passphrase_file> --type=PGP <file-name-1> <file-name-2>
        
        notes: The decrypted file will be placed in the same folder as the original file.

    5. To download public and private keys from Thycotic and import for user:  
        
         /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_encryption_handler.py --config_file=<config-json-file-path> --action=download --type=PGP

        The command will first determine which environment the host is in, then fetch the corresponding keys
         for the environment from Thycotic secret server, and finally import the keys to the environment.

        To check if keys are imported properly, you can check by executing:

            gpg2 --list-keys
            gpg2 --list-secret-keys

    6. To export public and private keys and upload to Thycotic:
        
         /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_encryption_handler.py --config_file=<config-json-file-path> --action=upload --type=PGP

        When the command is executed, 
        first it will run
            gpg2 --output /tmp/public_key.asc --no-tty --armor --export 
        and
            gpg2 --output /tmp/private_key.asc --no-tty --armor --export-secret-key --batch --pinentry-mode=loopback --passphrase_file /path/to/passphrase_file 

        second it will upload both public_key.asc and private_key.asc to Thycotic 

        finally it will remove both *.asc files.
        
    7. To export public and private keys locally (useful for key exchange):
    
         /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_encryption_handler.py --config_file=<config-json-file-path> --action=export --type=PGP
         
    8. To import public and private keys from local directory (CWD):
    
         /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_encryption_handler.py --config_file=<config-json-file-path> --action=import --type=PGP

    """
    arg_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=description_text,
        epilog="Use Cases: \n {}".format(use_cases_text)
    )
    # noinspection PyTypeChecker
    arg_parser.add_argument(
        "--config_file",
        type=str,
        help="Config File",
        required=False,
        metavar="config.json"
    )
    # noinspection PyTypeChecker
    arg_parser.add_argument(
        "--action",
        type=str,
        help="Action to perform",
        required=True,
        choices=["encrypt", "decrypt", "import", "export", "upload", "download", "generate"]
    )
    arg_parser.add_argument(
        "--type",
        nargs="?",
        type=str,
        help="Encryption type",
        required=False,
        choices=["PGP"],
        default="PGP"
    )
    arg_parser.add_argument(
        "paths",
        type=str,
        nargs="*",
        help="Paths of files or directories to be encrypted or decrypted. It can be a file, directory, or a list of both."
    )
    arg_parser.add_argument(
        '-p', '--passphrase_file', type=str, default=os.path.join(os.getenv('HOME'), '.passphrase'),
        help='Passphrase file for encrypt/decrypt (Only user should have read)')
    arg_parser.add_argument(
        '-r', '--recipient', type=str,
        help='Recipient of encrypted files.')
    arg_parser.add_argument(
        '-n', '--no_recurse', action='store_true',
        help='Disallow recursion when encrypting or decrypting'
    )
    arg_parser.add_argument(
        '-d', '--delete_original', action='store_true',
        help='Delete original file once decrypted or encrypted'
    )

    args = arg_parser.parse_args(args)

    if args.action in ['encrypt', 'decrypt'] and args.paths == []:
        arg_parser.print_help()
        ams_logger.error('Encrypt/decrypt require paths.')
        exit(1)

    return args


def _process_args(args):
    ams_config = AMSConfig(args.config_file)

    for arg, value in vars(args).items():
        ams_logger.debug('{}={}'.format(arg, value))

    return ams_config, args.action, args.type, args.paths, args.passphrase_file, \
           args.recipient, not args.no_recurse, args.delete_original


def _check_passphrase_file(passphrase_file):
    try:
        perms = os.stat(passphrase_file)
        if oct(perms[ST_MODE])[-2:] != '00':
            raise AttributeError('File permission of {} not safe for storing passphrase, should be 0600'
                                 .format(oct(perms[ST_MODE])[-4:]))
    except OSError:
        ams_logger.warning('Passphrase file not found. {}'.format(passphrase_file))
    except AttributeError as e:
        ams_logger.error(str(e))
        exit(1)
    return passphrase_file


def _store_passphrase(passphrase, passphrase_file):
    tmp_umask = os.umask(0077)
    try:
        ams_logger.info('Writing passphrase to passphrase_file: {}'.format(passphrase_file))
        with open(passphrase_file, 'w+') as p:
            p.write(passphrase.strip('"'))
    except Exception as e:
        ams_logger.error('Unable to write to passphrase_file: {}'.format(passphrase_file))
    finally:
        os.umask(tmp_umask)


def _check_len(paths, action):
    if len(paths) == 0:
        text = (
            "Files to {} is not provided to {}. "
            "Please check the syntax by turning on the --help flag.".format(action, __name__)
        )
        ams_logger.error(text)
        sys.exit(1)


def _get_passphrase_from_file(passphrase_file):
    _check_passphrase_file(passphrase_file)
    passphrase = None
    try:
        with open(passphrase_file, 'r') as f:
            passphrase = f.read().strip()
    except:
        ams_logger.info('No passphrase found in passhprase_file: {}.'.format(passphrase_file))
    return passphrase


def main(args=None):
    args = _parse_args(args)

    ams_config, action, type_, paths, passphrase_file, recipient, recurse, delete = _process_args(args)

    if ams_config.debug:
        ams_logger.set_debug(True)
    ams_defaults = AMSDefaults()

    try:
        if type_ == "PGP":
            gpg_model = AMSGpgModel(ams_config, recurse)

            # load secret from config file
            secrets = _get_secret_of_current_host(ams_config)

            if action == 'generate':
                param_file = raw_input('Optional path to existing parameters file: ') or None
                name = raw_input('Name ({}): '.format(getpass.getuser())) or getpass.getuser()
                email = raw_input('Email ({}@wnt.sas.com): '.format(name)) or '{}@wnt.sas.com'.format(name)
                passphrase = getpass.getpass('Passphrase: ') or None
                key_id = gpg_model.generate_keys(params_file=param_file, name=name, email=email, passphrase=passphrase)
                prompt = raw_input('Would you like to upload keys to thycotic? ').lower()
                if prompt in ['y', 'yes']:
                    ams_logger.info('Uploading key {} to thycotic.'.format(key_id))
                    action = 'upload'

            if action == 'encrypt':
                _check_len(paths, action)
                try:
                    gpg_model.encrypt(recipient, paths, delete)
                except AssertionError as e:
                    ams_logger.error(e.message)
                    sys.exit(1)

            elif action == "decrypt":
                _check_len(paths, action)

                passphrase = _get_passphrase_from_file(passphrase_file)
                if passphrase is None:
                    if len(secrets) > 0:
                        for secret in secrets:
                            try:
                                secret_server = AMSSecretServer(username=ams_config.decrypt(secret.username),
                                                                password=ams_config.decrypt(secret.password),
                                                                domain=secret.domain)
                            except Exception as e:
                                ams_logger.error('Unable to connect to Secret Server')
                                exit(1)
                            try:
                                tmp_passphrase = secret_server.get_secret_field(secret_id=secret.secret_id,
                                                                                slug='passphrase')
                                if tmp_passphrase:
                                    _store_passphrase(tmp_passphrase, passphrase_file)
                                    break
                            except Exception as e:
                                ams_logger.warning('Unable to retrieve passphrase from secret_id: {}.'
                                                   .format(secret.secret_id))
                                tmp_secret = secret_server.get_secret_by_id(secret_id=secret.secret_id)
                                ams_logger.warning('Secret expected to be of type GPG with template_ID: 6052, instead '
                                                   'found type: {} with template_ID: {}'
                                                   .format(tmp_secret['secretTemplateName'],
                                                           tmp_secret['secretTemplateId']))
                    else:
                        ams_logger.error('No matching secrets found and no valid passphrase_file provided. ')
                try:
                    gpg_model.decrypt(passphrase_file, paths, delete)
                except AssertionError as e:
                    ams_logger.error(e.message)
                    sys.exit(1)

            elif action in ['export', 'upload']:
                passphrase = _get_passphrase_from_file(passphrase_file)

                if passphrase is None:
                    ams_logger.info('The passphrase_file: {} is either missing or inaccessible, attempting to prompt '
                                    'for passphrase.'.format(passphrase_file))
                    passphrase = getpass.getpass("Passphrase: ")
                    _store_passphrase(passphrase, passphrase_file)

                gpg_model.export_public_keys(public_key_file)
                gpg_model.export_secret_keys(private_key_file, passphrase_file)

                if action == 'upload':
                    login = _prompt_thycotic_credentials()
                    # second upload keys to Thycotic
                    ams_logger.info("Start to upload keys to Thycotic.")
                    secret_server = AMSSecretServer(username=login['username'],
                                                    password=login['password'],
                                                    domain=login['domain'])

                    if not login['secret_id']:
                        ams_logger.info('No secret configured, attempting to create. Looking for environment in config.')
                        try:
                            tla = ams_config.get_my_environment().tla
                        except AMSConfigException:
                            tla = ''
                            ams_logger.warning('Environment not found in provided config, bypassing.')
                        if not tla:
                            environment = AMSEnvironment(new_config=True)
                            tla = re.sub('[0-9]+.*', '', environment.my_hostname)
                        folders = secret_server.search_folders(tla)
                        folder = None

                        secret_name = raw_input('Secret Name ({}_PGP): '.format(tla))
                        secret_name = '{}_PGP'.format(tla) if not secret_name else secret_name

                        if 'records' in folders.keys():
                            if len(folders['records']) == 1:
                                folder = folders['records'][0]
                                ams_logger.info('Creating secret in folder: {} id: {}'
                                                .format(folder['folderPath'], folder['id']))
                            else:
                                ams_logger.warning('Found {} matching folders, since != 1 we will create new folder.'
                                                   .format(len(folders['records'])))
                                folder_name = raw_input('Name of folder to create ({}): '.format(tla))
                                folder = secret_server.create_folder(folder_name if folder_name else tla)
                        else:
                            ams_logger.error('Unexpected scenario, folder search did not return as expected')

                        # Now we actually create the secret
                        existing_secrets = secret_server.search_secrets(secret_name=secret_name,
                                                                        folder_id=folder['id'])
                        if 'records' in existing_secrets.keys() and len(existing_secrets['records']) > 0:
                            ams_logger.error('Existing PGP secret matching name: "{}" in folder_id: "{}" detected but '
                                             'not configured, refusing overwrite'.format(secret_name, folder['id']))
                            exit(1)
                        secret_response = secret_server.create_secret(secret_name=secret_name,
                                                                      secret_type_id='6052',
                                                                      items=[],
                                                                      folder_id=folder['id'])
                        login['secret_id'] = secret_response['id']

                    secret_server.upload_file_attachment(
                        secret_id=login['secret_id'],
                        slug='public-key',
                        file_path=public_key_file
                    )
                    secret_server.upload_file_attachment(
                        secret_id=login['secret_id'],
                        slug='private-key',
                        file_path=private_key_file
                    )
                    secret_server.update_secret_field(
                        secret_id=login['secret_id'],
                        slug='passphrase',
                        value=passphrase
                    )

                    if path.exists(public_key_file):
                        os.remove(public_key_file)
                        ams_logger.info("{} has been removed.".format(public_key_file))
                    if path.exists(private_key_file):
                        os.remove(private_key_file)
                        ams_logger.info("{} has been removed.".format(private_key_file))

            elif action in ['import', 'download']:
                if action == 'download':
                    # get credentials
                    login = _prompt_thycotic_credentials()

                    secret_server = AMSSecretServer(username=login['username'],
                                                    password=login['password'],
                                                    domain=login['domain'])

                    # TODO I don't remember, but when something blows up hopefully this will help.

                    # retrieve passphrase from Thycotic
                    passphrase = secret_server.get_secret_field(
                        secret_id=login['secret_id'],
                        slug='passphrase'
                    )

                    # cache passphrase for local use
                    _store_passphrase(passphrase, passphrase_file)

                    # download key files
                    secret_server.download_file_attachment(login['secret_id'], 'public-key', public_key_file)
                    secret_server.download_file_attachment(login['secret_id'], 'private-key', private_key_file)

                gpg_model.import_keys(os.path.join(os.getcwd(), private_key_file))
                # Importing public key after private key is duplicative but if they don't match...
                gpg_model.import_keys(os.path.join(os.getcwd(), public_key_file))

    except KeyboardInterrupt:
        print("{} User killed process with ctrl+c...".format(os.linesep))
        # noinspection PyUnboundLocalVariable
        sys.exit(128)
    except OSError as e:
        print(
            "{}Process exited with a OSError exception: {}{}".format(
                os.linesep, str(e), os.linesep)
        )
        # noinspection PyUnboundLocalVariable
        sys.exit(1)
    except AMSSecretException as e:
        ams_logger.error(e.message)
        sys.exit(1)
    except AMSEncryptionException as e:
        ams_logger.error(e.message)
        sys.exit(1)
    except AMSConfigException as e:
        sys.exit(1)
    except Exception as e:
        # noinspection PyUnboundLocalVariable
        ams_logger.error(
            "Caught an exception running {file}: {exception}".format(
                file=__file__, exception=str(e))
        )
        ams_logger.error("Traceback: " + traceback.format_exc())

        description = "Error message: {}".format(str(e))
        description += "\n\nStack Trace:\n"
        description += traceback.format_exc()

        sys.exit(1)


def _get_secret_of_current_host(config):
    """Returns the secret object that matches the env_type of the environment at runtime"""
    secrets = config.get_secret_by_env_type()
    ams_logger.debug(
        "Secret(s) associated with env {hostname} is {secrets} ".format(
            hostname=socket.getfqdn(), secrets=repr(secrets)
                    )
    )

    return secrets


def _get_system_user_credentials(ams_config):
    ams_defaults = AMSDefaults()
    username = ams_config.decrypt(ams_defaults.thycotic_func_username)
    password = ams_config.decrypt(ams_defaults.thycotic_func_password)
    return password, username


def _prompt_thycotic_credentials():
    # prompt for Thycotic username and password
    login = {
        'username': raw_input("Thycotic username: ").strip(),
        'password': getpass.getpass("Thycotic password: "),
        'domain': raw_input("Thycotic domain: ").strip(),
        'secret_id': raw_input('Secret_ID (create if empty): ').strip()
    }
    return login


if __name__ == "__main__":
    main()
