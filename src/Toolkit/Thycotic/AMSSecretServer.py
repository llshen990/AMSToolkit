import os.path
import json
import requests
import logging
from Toolkit.Thycotic.AMSSecretConstants import SECRET_SEVER_ROOT, SECRET_SERVER_API
from Toolkit.Thycotic.Secrets.AMSPasswordSecret import AMSPasswordSecret
from Toolkit.Exceptions import AMSSecretException


class AMSSecretServer(object):
    """
    This is the REST implementation of the Thycotic Secret Server.
    Doc site: https://securevault.sas.com/secretserver/Documents/restapi/WinAuth/#/definitions/
    """
    def __init__(self, username, password, domain='', https_proxy=None):
        try:
            self.logger = logging.getLogger("AMS")
        except:
            self.logger = logging.getLogger()

        if https_proxy and len(https_proxy) > 0:
            self.logger.info("Setting https proxy to "+str(https_proxy))
            os.environ["https_proxy"] = https_proxy

        self.session = requests.Session()
        self._get_auth_token(username, password, domain)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def _get_auth_token(self, username, password, domain):
        self.logger.info("Logging into Thycotic ({domain}) as {user}.".format(domain=domain, user=username))

        headers = {
            "Accept": "application/json",
        }

        # Just ugh, way to be consistent thycotic.
        if domain:
            credentials = {
                "username": username.encode('utf-8'),
                "password": password.encode('utf-8'),
                "domain": domain,
                "grant_type": "password"
            }
            headers = {"Content-Type": "application/json"}
        else:
            credentials = ("username={}&password={}&grant_type=password&domain={}".format(username, password, domain)).encode('utf-8')
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

        url = SECRET_SEVER_ROOT + "/oauth2/token"
        try:
            response = requests.post(url, data=credentials, headers=headers)
        except Exception as e:
            self.logger.error("Caught an unexpected exception: " + str(e))
            raise AMSSecretException("Invalid Credentials. Failed to logged in as {user} and domain={domain}.".format(user=username, domain=domain))

        if response.status_code == 200:
            try:
                self.logger.info("Successfully logged in as {user}.".format(user=username))
                self.session.headers = {
                    "Authorization": "Bearer " + response.json()["access_token"],
                    "Accept": "application/json",
                    "content-type": "application/json"
                }
            except Exception as e:
                print(e)
        else:
            raise AMSSecretException("Invalid Credentials. Failed to logged in as {user} and domain={domain}. Response status_code={status_code} text={text}.".format(user=username, domain=domain, status_code=response.status_code, text=response.text))

    def process(self, response):
        if 200 <= response.status_code < 300:
            self.logger.info("HTTP call success.")
            self.logger.debug("response: {}".format(response))
            return response
        else:
            self.logger.error(
                "HTTP status code: {status_code}, response text: {response}".format(
                    status_code=response.status_code, response=response.text
                )
            )
            raise AMSSecretException("Failed to process request.")

    def expire_secret(self, secret_id):
        return self.process(self.session.post('{}/secrets/{}/expire'.format(SECRET_SERVER_API, secret_id)))

    def update_secret(self, secret_id, secret):
        return self.process(self.session.put('{}/secrets/{}'.format(SECRET_SERVER_API, secret_id), data=secret))

    def get_expiration_thycotic(self, secret_id):
        try:
            return self.get_summary(secret_id)['daysUntilExpiration']
        except KeyError as e:
            self.logger.error('No expiration found in thycotic for secret_id: {}'.format(secret_id))

    def get_summary(self, secret_id):
        url = '{}/secrets/{}/summary'.format(SECRET_SERVER_API, secret_id)
        return self.process(self.session.get(url)).json()

    def get_secret_audit_by_id(self, secret_id):
        return self.process(self.session.get('{}/secrets/{}/audits'.format(SECRET_SERVER_API, secret_id)))

    def update_secret_field(self, secret_id, slug, value):
        url = '{}/secrets/{}/fields/{}'.format(SECRET_SERVER_API, secret_id, slug)
        self.process(self.session.put(url, data=json.dumps({'value': value})))
        self.logger.info('Secret field ({}) updated successfully'.format(slug))

    def upload_file_attachment(self, secret_id, slug, file_path):
        filename = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            data = f.read()
            upload = {'fileName': filename,
                      'fileAttachment': [ord(x) for x in bytes(data)]}
        url = '{}/secrets/{}/fields/{}'.format(SECRET_SERVER_API, secret_id, slug)
        self.process(self.session.put(url, data=json.dumps(upload)))
        self.logger.info('File ({}) uploaded successfully as ({}).'.format(file_path, slug))

    def download_file_attachment(self, secret_id, slug, file_path):
        tmp_umask = os.umask(0077)
        try:
            filename = os.path.basename(file_path)
            if filename == file_path:
                file_path = os.path.join(os.getcwd(), file_path)
            with open(file_path, 'wb+') as f:
                contents = self.session.get('{}/secrets/{}/fields/{}'.format(SECRET_SERVER_API, secret_id, slug))
                f.write(contents.content)
        finally:
            os.umask(tmp_umask)

    def create_secret(self, secret_name, secret_type_id, items, folder_id):
        assert folder_id is not None
        assert secret_type_id is not None

        data = {
            "name": secret_name,
            "secretTemplateId": secret_type_id,
            "items": items,
            "siteId": 1,
            "folderId": folder_id,
        }

        self.logger.debug("Initiated a secret create request.")
        self.logger.debug("method: Post")
        self.logger.debug("url: {api}/secrets".format(api=SECRET_SERVER_API))
        self.logger.debug("data: {}".format(data))

        response = self.process(
            self.session.post(SECRET_SERVER_API + "/secrets", json=data)
        )

        secret_saved = response.json()

        self.logger.info("new secret id: {}".format(secret_saved["id"]))
        self.logger.debug("HTTP response obj: \n{}".format(secret_saved))

        return secret_saved

    def get_secret_field(self, secret_id, slug):
        self.logger.debug(
            "Retrieving secret field {slug} for {id}".format(id=secret_id, slug=slug)
        )
        self.logger.debug("method: Get")

        url = "{api}/secrets/{id}/fields/{slug}".format(
            api=SECRET_SERVER_API, id=secret_id, slug=slug
        )
        self.logger.debug("url: {}".format(url))

        response = self.process(self.session.get(url))

        try:
            value = response.content
        except:
            value = response

        # remove pairs of double and single quotes that are around values
        if (value[0] == value[-1]) and value.startswith(("'", '"')):
            return value[1:-1]
        return value

    def get_secret_by_id(self, secret_id):
        self.logger.debug("Retrieving secret {}".format(secret_id))
        self.logger.debug("method: Get")

        url = "{api}/secrets/{id}".format(api=SECRET_SERVER_API, id=secret_id)
        self.logger.debug("url: {}".format(url))

        try:
            response = self.process(self.session.get(url))
            return response.json()
        except:
            return None

    def get_amspassword_secret(self, secret_id):
        try:
            secret = AMSPasswordSecret()
            secret.username = self.get_secret_field(secret_id=secret_id, slug='username')
            secret.password = self.get_secret_field(secret_id=secret_id, slug='password')
            return secret
        except Exception as e:
            self.logger.info(("Problem finding fields Username or Password: message is {}".format(e)))

    def search_folders(self, folder_name, parent_folder=None):
        search_filter = ['filter.searchText={}'.format(folder_name)]
        if parent_folder is not None:
            search_filter.append('filter.parentFolderId={}'.format(parent_folder))
        url = '{}/folders?{}'.format(SECRET_SERVER_API, '&'.join(search_filter))
        return self.process(self.session.get(url)).json()

    def search_secrets(self, secret_name, folder_id='', recursive=False):
        search_filter = ['filter.searchText={}'.format(secret_name)]
        if folder_id:
            search_filter.append('filter.folderId={}'.format(folder_id))
        if recursive:
            search_filter.append('filter.includeSubFolders=true')
        url = '{}/secrets?{}'.format(SECRET_SERVER_API, '&'.join(search_filter))
        return self.process(self.session.get(url)).json()

    def create_folder(self, folder_name, parent_folder=-1):
        inherit = True
        if parent_folder == -1:
            inherit = False
        if len(self.search_folders(folder_name, parent_folder)['records']) > 0:
            self.logger.info('Folder: "{}" already exists in parent folder "{}"'.format(folder_name, parent_folder))
            resp = {}
        else:
            url = '{}/folders'.format(SECRET_SERVER_API)
            data = {'folderName': folder_name,
                    'folderTypeId': 1,
                    'inheritPermissions': inherit,
                    'inheritSecretPolicy': inherit,
                    'parentFolderId': parent_folder,
                    'secretPolicyId': 0}
            resp = self.process(self.session.post(url=url, json=data)).json()
        return resp
