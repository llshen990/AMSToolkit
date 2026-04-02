import os
from zeep import Client
from requests import Session

from Toolkit.Thycotic.Secrets.AMSPasswordSecret import AMSPasswordSecret
from Toolkit.Exceptions import AMSSecretException
from Toolkit.Lib.Helpers import FileSoapTransport


class AMSSecretServer(object):
    def __init__(self, ams_config, username, password, domain, https_proxy=None, wsdl='https://securevault.sas.com/secretserver/webservices/SSWebservice.asmx?wsdl'):
        self.AMSConfig = ams_config
        if https_proxy and len(https_proxy) > 0:
            self.AMSConfig.AMSLogger.info("Setting https proxy to "+str(https_proxy))
            os.environ["https_proxy"] = https_proxy
        self.session = Session()
        transport = FileSoapTransport(session=self.session)
        self.client = Client(wsdl, transport=transport)
        self.AMSConfig.AMSLogger.info("Logging into Thycotic username=<" + str(username) + "> domain=<" + str(domain) + ">")
        self.token = self.client.service.Authenticate(username, password, "", domain)

        # Check token to ensure authenticated
        if not self.token or not self.token.Token or self.token.Errors:
            self.AMSConfig.AMSLogger.info("Invalid credentials")
            raise AMSSecretException('Invalid credentials')

    @staticmethod
    def _get_result(key, soap_result):
        if soap_result is None:
            return "Success"
        if 'Errors' not in soap_result:
            raise Exception("Invalid Request")
        if soap_result['Errors'] is None and key in soap_result:
            return soap_result[key]
        else:
            return soap_result['Errors']

    def _get_secret_by_fieldname(self, secret, field):
        # First check for the named fields
        try:
            # First check in the free-form Notes for the "Field:"
            for item in secret.Items.SecretItem:
                if item['FieldName'] == 'Notes':
                    if item['Value']:
                        # TODO: need a secure logging or masking logging mechanism
                        self.AMSConfig.AMSLogger.debug("Found notes:" + str(item['Value']))
                        lines = item['Value'].split('\n')
                        for line in lines:
                            if line.startswith(field + ':'):
                                return line.split(':')[1].strip()
                    else:
                        self.AMSConfig.AMSLogger.info("No notes for secret")
            self.AMSConfig.AMSLogger.info("No field " + field + " found in Notes checking specific fields")
            for item in secret.Items.SecretItem:
                if item['FieldName'] == field:
                    return item['Value']
            self.AMSConfig.AMSLogger.info(("Cannot find field {0} in secret".format(field)))
        except Exception as e:
            import traceback
            traceback.print_exc(e)
            self.AMSConfig.AMSLogger.info(("Problem finding field {0}: message is {1}".format(field, e)))
        return None

    def get_secret_json(self, secret_id):
        return AMSSecretServer._get_result('Secret', self.client.service.GetSecret(self.token.Token, secret_id))

    def get_secret_by_id(self, secret_id):
        json = self.get_secret_json(secret_id)

        # For now we just support a PasswordSecret which is a UserName and Password pair
        # We'll add support for other secret implementations in the future here
        username = self._get_secret_by_fieldname(json, 'UserName')
        if not username:
            username = self._get_secret_by_fieldname(json, 'Username')
        password = self._get_secret_by_fieldname(json, 'Password')

        if username and password:
            return AMSPasswordSecret(username=username, password=password)
        else:
            return None

    def get_secret_audit_by_id(self, secret_id):
        return AMSSecretServer._get_result('SecretAudits', self.client.service.GetSecretAudit(self.token.Token, secret_id))

    def expire_secret(self, secret_id):
        return AMSSecretServer._get_result('SecretAudits', self.client.service.ExpireSecret(self.token.Token, secret_id))

    def update_secret(self, secret):
        return AMSSecretServer._get_result('SecretAudits', self.client.service.UpdateSecret(self.token.Token, secret))

    def upload_file_attachment_by_item_id(self, secret_id, secret_item_id, file_path):
        filename = os.path.basename(file_path)
        with open(file_path, 'rb') as fp:
            data = fp.read()
            upload_file_args = {'token': str(self.token.Token),
                                'secretId': int(secret_id),
                                'secretItemId': int(secret_item_id),
                                'fileData': bytes(data),
                                'fileName': str(filename)}
        # Tell the server to upload file
        result = AMSSecretServer._get_result('UploadFileAttachmentByItemId',
                                           self.client.service.UploadFileAttachmentByItemId(**upload_file_args))
        if result == 'Success':
            self.AMSConfig.AMSLogger.info(
                "Success: file {file_path} has been uploaded and attached to secret {secret_id}".format(
                    file_path=file_path,
                    secret_id=secret_id
                )
            )

