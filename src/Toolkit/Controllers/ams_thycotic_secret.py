import os
import sys
import argparse
import traceback
import json
import getpass

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)


from Toolkit.Lib import AMSLogger
from Toolkit.Exceptions import (
    AMSExceptionNoEventNotification,
    AMSConfigException,
    AMSSecretException,
)
from Toolkit.Config import AMSConfig
from Toolkit.Models import AMSSecretServerModel
from Toolkit.Thycotic.Secrets.AMSPgpSecret import AMSPgpSecret
from Toolkit.Thycotic.Secrets.AMSPasswordSecret import AMSPasswordSecret
from Toolkit.Thycotic.Secrets.AMSUnixAccountSshSecret import AMSUnixAccountSshSecret
from Toolkit.Thycotic.AMSSecretConstants import (
    all_secret_types,
    all_folder_names,
    TYPE_PGP,
    TYPE_PASSWORD,
    value_to_name,
    TYPE_UNIX_ACCOUNT_SSH,
)


ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + ".log")


def _input(prompt):
    return raw_input(prompt).strip()


def _load_config(file_path):
    with open(file_path, "r") as content:
        return json.load(content)


def _save_to_file(secret_saved, input_file, output_file):
    config_json = _load_config(input_file)

    with open(output_file, "w") as output:

        if "secrets" not in config_json.keys():
            config_json["secrets"] = {}
        secret_name = secret_saved.secret_name.strip()

        config_json["secrets"][secret_name] = vars(secret_saved)
        output.write(json.dumps(config_json, indent=2))

        ams_logger.info(
            "Secret {secret_name} has been persisted in {file_name} successfully.".format(
                secret_name=secret_name, file_name=output_file
            )
        )
        ams_logger.info(
            "For more details please see {url}".format(
                url=secret_saved.get_secret_url()
            )
        )


def _create_secret(secret_server_model, user_input_values):

    secret_type = user_input_values.get("i_secret_type")
    secret_name = user_input_values.get("i_secret_name")
    domain = user_input_values.get("i_domain")
    env = user_input_values.get("i_env")
    folder = user_input_values.get("i_folder")
    personal_username = user_input_values.get("i_personal_username")
    personal_password = user_input_values.get("i_personal_password")

    base_secret_attributes = {
        "secret_type": value_to_name(secret_type),
        "secret_name": secret_name,
        "domain": domain,
        "environment": env,
        "folder": value_to_name(folder),
    }

    if secret_type == TYPE_PGP:

        secret = AMSPgpSecret(
            description=user_input_values.get("i_description"),
            passphrase=user_input_values.get("i_passphrase"),
            **base_secret_attributes
        )

    elif secret_type == TYPE_UNIX_ACCOUNT_SSH:

        secret = AMSUnixAccountSshSecret(
            username=user_input_values.get("i_username"),
            password=user_input_values.get("i_password"),
            notes=user_input_values.get("i_notes"),
            machine=user_input_values.get("i_machine"),
            passphrase=user_input_values.get("i_passphrase"),
            **base_secret_attributes
        )

    elif secret_type == TYPE_PASSWORD:

        secret = AMSPasswordSecret(
            username=user_input_values.get("i_username"),
            password=user_input_values.get("i_password"),
            notes=user_input_values.get("i_notes"),
            resource=user_input_values.get("i_resource"),
            **base_secret_attributes
        )

    else:
        raise AMSSecretException(
            "Secret type {} is not supported yet.".format(secret_type)
        )

    secret_saved = secret_server_model.create_secret(
        username=personal_username,
        password=personal_password,
        domain=domain,
        secret=secret,
    )
    return secret_saved


def _prompt_user_inputs(arg_secret_type):
    print("There will be two steps in the process.")
    print("1 - provide your personal Thycotic credentials to log into")
    print("2 - provide new secret details")

    print("** step 1 **")

    i_domain = _input("Thycotic domain (vsp or carynt): ")
    i_personal_username = _input("Thycotic username: ")
    i_personal_password = getpass.getpass("Thycotic password: ")

    print("** step 2 **")

    if arg_secret_type not in all_secret_types():
        i_secret_type = _input(
            "* Secret Type ({}): ".format(" or ".join(all_secret_types()))
        )
    else:
        i_secret_type = arg_secret_type

    # show type specific prompts
    if i_secret_type == TYPE_PGP:
        user_input_values = AMSPgpSecret.prompt_user_input()
    elif i_secret_type == TYPE_UNIX_ACCOUNT_SSH:
        user_input_values = AMSUnixAccountSshSecret.prompt_user_input()
    elif i_secret_type == TYPE_PASSWORD:
        user_input_values = AMSPasswordSecret.prompt_user_input()
    else:
        raise AMSSecretException(
            "Secret type {type} is not supported yet. Valid options are {options}.".format(
                type=i_secret_type, options=", ".join(all_secret_types())
            )
        )

    i_env = _input("Environment (DEV or TEST or PROD (specify DEV, TEST, PROD if applies to all)): ")
    i_folder = _input(
        "Folder to store secret ({}): ".format(" or ".join(all_folder_names()))
    )

    user_input_values.update(
        {
            "i_env": i_env,
            "i_folder": i_folder,
            "i_secret_type": i_secret_type,
            "i_domain": i_domain,
            "i_personal_username": i_personal_username,
            "i_personal_password": i_personal_password,
        }
    )

    ams_logger.info("New secret details received.")
    ams_logger.debug("user_input_values={}".format(user_input_values))

    return user_input_values


def _process_args(args):
    config_file_path = str(args.config_file).strip()
    ams_logger.debug("config_file={}".format(config_file_path))

    # construct an AMSConfig object
    ams_config = AMSConfig(config_file_path)
    ams_logger.set_debug(ams_config.debug)

    # secret name
    arg_secret_name = str(args.secret_name).strip() if args.secret_name else None
    ams_logger.debug("secret_name={}".format(arg_secret_name))

    # secret type
    arg_secret_type = str(args.secret_type).strip()
    ams_logger.debug("secret_type={}".format(arg_secret_type))

    # action
    action = str(args.action).strip()
    ams_logger.debug("action={}".format(action))

    return action, ams_config, arg_secret_name, arg_secret_type, config_file_path


def _parse_args(args):
    if not args:
        args = sys.argv[1:]

    description_text = """Description: \n
    This is a controller that communicates with the Thycotic Secret Server to retrieve, audit, expire and create secrets.
    
    It currently supports creating secrets of the following secret template types, in Thycotic:
        1. Password
        2. GPG  
        3. Unix account (SSH)
        
    A Thycotic password secret includes a username, a password, a resource, and other meta fields.
    A Thycotic GPG secret includes a public key, a passphrase, a private (secret) key, a revocation certificate, a ownerrust, and other meta fields.
    A Thycotic Unix account (SSH) secret includes a unix account (machine, username and password), a SSH private key, 
      a SSH private key passphrase, and other meta fields.
      
    After a new secret has been created, the controller persists the Thycotic secret id and other fields in the secrets 
     section of the config file. The secret id can be used downstream for secret retrieval.
      
    Sample secrets section:
    "secrets": {
        "test secret 1": {
          "secret_type": "TYPE_PGP",
          "domain": "vsp",
          "description": "",
          "secret_items": null,
          "secret_id": 114571,
          "environment": "Dev",
          "secret_type_id": 6052,
          "folder_id": 23357,
          "passphrase": null,
          "folder": "TEST_Global",
          "secret_name": "test secret 1"
        }
    }
  
    
    Caveats: 
    1. Please note that this controller does not generate a new PGP key pair yet. You will need to generate a new key pair
       prior to calling this controller.
    2. Creating a Thycotic secret only supports interactive mode at the moment. This is because a user's credential is needed
       for authentication and authorization purposes. This also improves auditability of secret management in Thycotic.
    """
    use_cases_text = """
    == To retrieve a Thycotic secret ==
      coming soon
    
    == To audit a Thycotic secret ==
      coming soon
    
    == To expire a Thycotic secret ==
      coming soon
    
    == To create a Thycotic secret ==
    
    1. To create a new GPG secret:
    
        /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_thycotic_secret.py --config_file=amp_config.json --action=create --secret_type=PGP

    2. To create a new Unix account (SSH keys) secret:
    
        /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_thycotic_secret.py --config_file=amp_config.json --action=create --secret_type=Unix_Account_SSH
        
    3. To create a new password secret:
        /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_thycotic_secret.py --config_file=amp_config.json --action=create --secret_type=password
        
    """
    arg_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=description_text,
        epilog="Use Cases: \n {}".format(use_cases_text),
    )
    # noinspection PyTypeChecker
    arg_parser.add_argument(
        "--config_file", nargs="?", help="Config File", required=True
    )
    arg_parser.add_argument(
        "--secret_name", nargs="?", help="Secret Name", required=False
    )
    arg_parser.add_argument(
        "--secret_type",
        nargs="?",
        choices=all_secret_types(),
        help="Secret type to create",
        required=False,
    )
    arg_parser.add_argument(
        "--action",
        nargs="?",
        choices=["get", "json", "audit", "expire", "create"],
        help="Action to perform",
        default='get',
        required=False,
    )

    args = arg_parser.parse_args(args)

    return args


def main(args=None):

    args = _parse_args(args)

    (
        action,
        ams_config,
        arg_secret_name,
        arg_secret_type,
        config_file_path,
    ) = _process_args(args)

    if ams_config.new_config:
        raise AMSExceptionNoEventNotification(
            "Config file of {} does not currently exist.  You must specify a valid config.".format(
                args.config_file
            )
        )
    try:

        secret_server_model = AMSSecretServerModel(ams_config, arg_secret_name)

        if action == "audit":

            print(secret_server_model.audit_secret())

        elif action == "expire":

            print(secret_server_model.expire_secret())

        elif action == "json":

            print(secret_server_model.get_amspassword_secret())

        elif action == "create":

            user_input_values = _prompt_user_inputs(arg_secret_type)

            secret_saved = _create_secret(secret_server_model, user_input_values)

            _save_to_file(
                secret_saved, input_file=config_file_path, output_file=config_file_path
            )

        else:
            # DEFAULT ACTION OF GET
            print(secret_server_model.get_secret())
    except KeyboardInterrupt:
        print("{}User termination.  Exiting...".format(os.linesep))
    except AMSConfigException as e:
        print("Config exception occurred: " + str(e))
    except AMSSecretException:
        sys.exit(0)
    except Exception as e:
        ams_logger.error("Caught an exception: " + str(e))
        ams_logger.error("Traceback: " + traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
