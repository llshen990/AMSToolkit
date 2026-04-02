from json import dumps

from Toolkit.Thycotic.AMSSecretConstants import name_to_id
from Toolkit.Thycotic.AMSSecretConstants import SECRET_SEVER_ROOT


class AMSBaseSecret(object):
    """
    AMSBaseSecret can be used as the base class for all Thycotic secrets.
    The top level fields of a given secret object in Thycotic includes:
    - id: number
    - secret type: string
    - folder id: number
    - name: string
    - items: array

    Different secret types will contain a different list of secret items, stored in the `items` array.

    For example, a password secret would contain items with field name `UserName`, `Password`, `URL`, `Notes`.
    a pgp secret would contain items with field name `Private Key`, `Public Key`, `Passphrase`, `Revocation Certificate`,
    `Ownertrust` and `Description`.
    """
    def __init__(self, **kwargs):
        self.secret_id = kwargs.get('secret_id')
        self.secret_name = kwargs.get('secret_name')
        self.secret_type = kwargs.get('secret_type')
        self.secret_items = kwargs.get('secret_items') if kwargs.get('secret_items') else []
        self.folder = kwargs.get('folder')
        self.domain = kwargs.get('domain')
        self.environment = kwargs.get('environment')

        self.folder_id = name_to_id(self.folder)
        self.secret_type_id = name_to_id(self.secret_type)

    @staticmethod
    def prompt_user_input():
        i_secret_name = raw_input("* Secret name: ").strip()
        return {'i_secret_name': i_secret_name}

    def get_secret_url(self):
        if self.secret_id:
            return "{root}/app/#/secret/{id}/general".format(root=SECRET_SEVER_ROOT, id=self.secret_id)

    def _add_secret_items(self):
        pass

    def __str__(self):
        return vars(self)

    def __repr__(self):
        return dumps(vars(self), indent=2)
