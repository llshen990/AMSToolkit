import getpass
from Toolkit.Thycotic.Secrets.AMSBaseSecret import AMSBaseSecret
from Toolkit.Thycotic.Secrets.AMSSecretItem import AMSSecretItem


class AMSPasswordSecret(AMSBaseSecret):
    def __init__(self, **kwargs):
        super(AMSPasswordSecret, self).__init__(**kwargs)
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.notes = kwargs.get('notes')
        self.resource = kwargs.get('resource')

        self._add_secret_items()

    @staticmethod
    def prompt_user_input():
        base_inputs = super(AMSPasswordSecret, AMSPasswordSecret).prompt_user_input()
        i_username = raw_input("new username: ").strip()
        i_password = getpass.getpass("new password: ").strip()
        i_notes = raw_input("notes: ").strip()
        i_resource = raw_input("specify a uri resource: ").strip()

        combined_inputs = {'i_username': i_username, 'i_password': i_password, 'i_notes': i_notes, 'i_resource': i_resource}
        combined_inputs.update(base_inputs)
        return combined_inputs

    def _add_secret_items(self):
        if self.username:
            self.secret_items.append(AMSSecretItem(field_id=61, item_value=self.username))
        if self.password:
            self.secret_items.append(AMSSecretItem(field_id=7, item_value=self.password))
        if self.notes:
            self.secret_items.append(AMSSecretItem(field_id=8, item_value=self.notes))
        if self.resource:
            self.secret_items.append(AMSSecretItem(field_id=60, item_value=self.resource))

    def __str__(self):
        return self.__class__.__name__ + "[UserName=" + self.username + ", Password=" + self.password + "]"
