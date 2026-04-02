import getpass
from Toolkit.Thycotic.Secrets.AMSBaseSecret import AMSBaseSecret
from Toolkit.Thycotic.Secrets.AMSSecretItem import AMSSecretItem


class AMSPgpSecret(AMSBaseSecret):
    def __init__(self, **kwargs):
        super(AMSPgpSecret, self).__init__(**kwargs)
        self.description = kwargs.get('description')
        self.passphrase = kwargs.get('passphrase')

        self._add_secret_items()

    @staticmethod
    def prompt_user_input():
        base_inputs = super(AMSPgpSecret, AMSPgpSecret).prompt_user_input()
        i_description = raw_input("Secret description: ").strip()
        i_passphrase = getpass.getpass("Passphrase: ").strip()

        combined_inputs = {'i_description': i_description, 'i_passphrase': i_passphrase}
        combined_inputs.update(base_inputs)
        return combined_inputs

    def _add_secret_items(self):
        if self.description:
            content = "{desc} \n Environment: {env}".format(desc=self.description, env=self.environment)
            self.secret_items.append(AMSSecretItem(field_id=309, item_value=content))
        if self.passphrase:
            self.secret_items.append(AMSSecretItem(field_id=307, item_value=self.passphrase))

