import logging
from Toolkit.Exceptions import AMSSecretException
from Toolkit.Thycotic.Secrets.AMSBaseSecret import AMSBaseSecret
from Toolkit.Thycotic.Secrets.AMSPgpSecret import AMSPgpSecret
from Toolkit.Thycotic.AMSSecretServer import AMSSecretServer
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from Toolkit.Thycotic.AMSSecretConstants import id_to_value, value_to_id, TYPE_PGP


class AMSSecretServerModel(AbstractAMSBase):
    logger = logging.getLogger('AMS')

    def __init__(self, ams_config, secret_name):
        AbstractAMSBase.__init__(self, ams_config)
        if secret_name is not None:
            self.secret = self.AMSConfig.get_secret_by_name(secret_name)

    def get_secret(self):
        secret_server = AMSSecretServer(username=self.AMSConfig.decrypt(self.secret.username),
                                        password=self.AMSConfig.decrypt(self.secret.password),
                                        domain=self.secret.domain)
        return secret_server.get_amspassword_secret(self.secret.secret_id)

    def get_amspassword_secret(self):
        secret_server = AMSSecretServer(username=self.AMSConfig.decrypt(self.secret.username),
                                        password=self.AMSConfig.decrypt(self.secret.password),
                                        domain=self.secret.domain)
        return secret_server.get_amspassword_secret(self.secret.secret_id)

    @staticmethod
    def get_secret_field(username, password, domain, secret_id, slug):
        """
        returns
        """
        secret_server = AMSSecretServer(username=username, password=password, domain=domain)
        result = secret_server.get_secret_field(secret_id, slug)
        return result

    def expire_secret(self):
        secret_server = AMSSecretServer(username=self.AMSConfig.decrypt(self.secret.username),
                                        password=self.AMSConfig.decrypt(self.secret.password),
                                        domain=self.secret.domain)
        return secret_server.expire_secret(self.secret.secret_id)

    def audit_secret(self):
        secret_server = AMSSecretServer(username=self.AMSConfig.decrypt(self.secret.username),
                                        password=self.AMSConfig.decrypt(self.secret.password),
                                        domain=self.secret.domain)
        return secret_server.get_secret_audit_by_id(self.secret.secret_id)

    def create_secret(self, username, password, domain, secret):
        secret_server = AMSSecretServer(username=username, password=password, domain=domain)

        items = map(lambda item: {'fieldId': item.get('field_id'), 'itemValue': item.get('item_value')},
                    secret.secret_items)

        saved_secret = secret_server.create_secret(secret_name=secret.secret_name, secret_type_id=secret.secret_type_id,
                                                   items=items, folder_id=secret.folder_id)

        if secret.secret_type_id == value_to_id(TYPE_PGP):

            return AMSPgpSecret(secret_id=saved_secret['id'], secret_name=saved_secret['name'],
                                secret_type=id_to_value(saved_secret['secretTemplateId']),
                                folder=id_to_value(saved_secret['folderId']),
                                environment=secret.environment,
                                domain=secret.domain,
                                passphrase="*****",
                                description=secret.description)

        else:

            return AMSBaseSecret(secret_id=saved_secret['id'], secret_name=saved_secret['name'],
                                 secret_type=id_to_value(saved_secret['secretTemplateId']),
                                 folder=id_to_value(saved_secret['folderId']),
                                 environment=secret.environment,
                                 domain=secret.domain)

    def upload_file_attachment(self, username, password, domain, secret_id, secret_slug, file_path):
        item_id = self._get_item_id(username=username, password=password, domain=domain,
                                    secret_id=secret_id, secret_slug=secret_slug)

        secret_server = AMSSecretServer(self.AMSConfig, username=username,
                                        password=password,
                                        domain=domain)

        return secret_server.upload_file_attachment_by_item_id(
            secret_id=secret_id,
            secret_item_id=item_id,
            file_path=file_path)

    def _get_item_id(self, username, password, domain, secret_id, secret_slug):
        # using the REST api instead of the SOAP api to retrieve json
        # in order to find secret item by slug, which is unique and only available in the REST api.
        # The alternative is to find secret item by fieldID, which is a number.
        # The alternative is less ideal, because the fieldID could be different from domain to domain.
        secret_server = AMSSecretServer(username=username, password=password, domain=domain)
        secret_json = secret_server.get_secret(secret_id)
        try:
            item = filter(lambda item: item['slug'] == secret_slug, secret_json['items'])
            item_id = item[0]['itemId']
        except KeyError:
            self.logger.debug("secret_json: {}".format(secret_json))
            raise AMSSecretException('Error occurred when filtering secret item for {}'.format(secret_id))
        except IndexError:
            raise AMSSecretException(
                'No secret item with slug {slug} associated with secret {secret_id} is found.'.format(
                    slug=secret_slug, secret_id=secret_id)
            )
        return item_id
