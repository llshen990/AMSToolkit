#!/usr/bin/env /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python
import sys
import os
import requests
import json
import argparse

from Toolkit.Lib import AMSLogger
from Toolkit.Config import AMSConfig
from Toolkit.Thycotic import AMSSecretServer

HTTP_PROXY = "http://webproxy.vsp.sas.com:3128"
HTTPS_PROXY = "http://webproxy.vsp.sas.com:3128"
proxy_dict = {'http': HTTP_PROXY, 'https': HTTPS_PROXY}

ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')


def get_token():
    try:
        config = AMSConfig()
        secret_server = AMSSecretServer(username=config.decrypt(config.AMSDefaults.thycotic_func_username), password=config.decrypt(config.AMSDefaults.thycotic_func_password), domain="")
        ams_logger.info("Logged into secret server")

        secret = secret_server.get_secret_by_id(131020)
        if secret:
            client_id = secret_server.get_secret_field(131020, 'ClientId')
            client_secret = secret_server.get_secret_field(131020, 'ClientSecret')
            tenant_id = secret_server.get_secret_field(131020, 'Scope')
            ams_logger.info("Retreived secret info client_id={}".format(client_id))
        else:
            ams_logger.error("No secret found?!")
            return ''

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': client_secret, 'scope': 'https://graph.microsoft.com/.default'}
        token_url = "https://login.microsoftonline.com/{}/oauth2/v2.0/token".format(tenant_id)

        access_token_response = requests.post(token_url, headers=headers, data=data, proxies=proxy_dict)
        ams_logger.info("Status code to get access token: status_code={}".format(access_token_response.status_code))
        if access_token_response.status_code in [200]:
            ams_logger.info("200 status code!")
            ams_logger.debug(access_token_response.status_code)
        else:
            return ''

        tokens = json.loads(access_token_response.text)
        access_token = tokens['access_token']
        ams_logger.debug("access token: " + access_token)
        return access_token

    except Exception as e:
        ams_logger.error('Exception {}'.format(str(e)))
        return ''

def upload_file(token, input_file, sharepoint_id, drive_id, folder_id, destination_name):
    read_path = open(input_file, 'rb').read()
    ams_logger.info('Uploading file {} to sharepoint path {}'.format(input_file, destination_name))
    url = "https://graph.microsoft.com/v1.0/sites/{}/drives/{}/items/{}:/{}:/content/".format(sharepoint_id, drive_id, folder_id, destination_name)
    headers = {'Authorization': 'Bearer {}'.format(token)}
    # Put the new content
    try:
        r = requests.put(url, headers=headers, data=read_path, proxies=proxy_dict)
        ams_logger.info('Status code={}'.format(r.status_code))
    except r.status_code not in [200,201]:
        ams_logger.error("Status code to upload file: " + r.status_code)
    return

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--destination_name", nargs='?', type=str, help="Name of new file to create in SharePoint", required=True)
    arg_parser.add_argument("--input_file", nargs='?', type=str, help="File to read", required=True)
    # TODO: this is hardcoded for the ETL Ops sharepoint "Document Library > ETL Ops Support Docs > Automated Customers" folder
    #arg_parser.add_argument("--folder_id", nargs='?', type=str, help="ID of SharePoint resource", required=True)
    #arg_parser.add_argument("--drive_id", nargs='?', type=str, help="ID of SharePoint resource", required=True)
    #arg_parser.add_argument("--sharepoint_id", nargs='?', type=str, help="ID of SharePoint resource", required=True)

    args = arg_parser.parse_args()

    try:
        sharepoint_id = 'sasoffice365.sharepoint.com,b66ddb78-b591-46b2-a817-1e411eb47be5,52f56ec6-819b-4814-a259-87a14edee4f0'
        drive_id  = 'b!eNtttpG1skaoFx5BHrR75cZu9VKbgRRIolmHoU7e5PDJBRv-PeEEQqgas_qqsFd-'
        folder_id = '01Z4FSI5ZETQSJNYP745A364KN56OWI6GA'
        token = get_token()
        if token:
            upload_file(token, args.input_file, sharepoint_id, drive_id, folder_id, args.destination_name)
            sys.exit(0)
        else:
            ams_logger.error("Could not obtain authentication token")
            sys.exit(1)
    except IOError as e:
        ams_logger.error(str(e))
        sys.exit(1)
