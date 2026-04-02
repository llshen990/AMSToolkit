from Toolkit.Thycotic.Secrets.AMSBaseSecret import AMSBaseSecret
from Toolkit.Thycotic.Secrets.AMSSecretItem import AMSSecretItem


class AMSUnixAccountSshSecret(AMSBaseSecret):
    def __init__(self, **kwargs):
        super(AMSUnixAccountSshSecret, self).__init__(**kwargs)
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.machine = kwargs.get('machine')
        self.private_key = kwargs.get('private_key')
        self.passphrase = kwargs.get('passphrase')
        self.notes = kwargs.get('notes')

        self._add_secret_items()

    @staticmethod
    def prompt_user_input():
        base_inputs = super(AMSUnixAccountSshSecret, AMSUnixAccountSshSecret).prompt_user_input()
        i_username = raw_input("new username: ").strip()
        i_password = raw_input("new password: ").strip()
        i_machine = raw_input("machine: ").strip()
        i_passphrase = raw_input("passphrase: ").strip()
        i_notes = raw_input("notes: ").strip()

        combined_inputs = {'i_username': i_username, 'i_password': i_password, 'i_machine': i_machine,
                           'i_passphrase': i_passphrase, 'i_notes': i_notes}
        combined_inputs.update(base_inputs)
        return combined_inputs

    def _add_secret_items(self):
        if self.username:
            self.secret_items.append(AMSSecretItem(field_id=111, item_value=self.username))
        if self.password:
            self.secret_items.append(AMSSecretItem(field_id=110, item_value=self.password))
        if self.machine:
            self.secret_items.append(AMSSecretItem(field_id=108, item_value=self.machine))
        if self.passphrase:
            self.secret_items.append(AMSSecretItem(field_id=190, item_value=self.passphrase))
        if self.notes:
            self.secret_items.append(AMSSecretItem(field_id=109, item_value=self.notes))
