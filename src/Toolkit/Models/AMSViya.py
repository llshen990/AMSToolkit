import re
import time
import json
import logging
import requests
import ConfigParser
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from Toolkit.Exceptions import AMSException


class AMSViya(AbstractAMSBase):
    def __init__(self, base_url=None, client_id=None, client_secret=None, authfile=None, profile='Default', verbose=False, create=False):
        self.success = None
        self.limit = re.compile('\?')
        self.logger = logging.getLogger('AMS')
        self.access_token = None
        self.verbose = verbose
        self.profile = profile
        if authfile is not None:
            self.authfile = authfile
            try:
                self._load_auth(authfile, profile)
            except Exception as e:
                raise e
        else:
            self.authfile = authfile
            self.base_url = base_url
            self.client_id = client_id
            self.client_secret = client_secret
        self.session = requests.Session()
        if create:
            self._get_access(create)
        self._generate_token()
        print("token {}".format(self.access_token))

    @staticmethod
    def jprint(obj):
        print(json.dumps(obj, indent=3))

    def _get_access(self, client_token):
        headers = {'X-Consul-Token': client_token}
        url = '{}/SASLogon/oauth/clients/consul?callback=false&serviceId=app'.format(self.base_url)
        try:
            r = requests.post(url=url, headers=headers)
            if r.status_code == 200:
                tmp_access_token = r.json()['access_token']
                self._gen_client(tmp_access_token)
        except Exception as e:
            self.logger.error('Unable to obtain bearer token in order to create client.\n'.format(e))

    def _gen_client(self, token):
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer {}'.format(token)}
        url = '{}/SASLogon/oauth/clients/'.format(self.base_url)
        data = {'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': ['*', 'openid'],
                'authorized_grant_types': 'client_credentials',
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'authorities': 'SASAdministrators'}
        try:
            r = requests.post(url=url, headers=headers, data=json.dumps(data))
            if r.status_code == 200:
                self.logger.info('Client_id: [{}] created'.format(self.client_id))
        except Exception as e:
            self.logger.error('Client_id [{}] was not created\n{}'.format(self.client_id, str(e)))

    def get_log_location(self, job_execution):
        if len(job_execution) == 36:
            job_execution = 'jobExecution/jobs/' + job_execution
        try:
            resp = self.make_request('GET', job_execution)
            return resp.json()['logLocation']
        except Exception as e:
            self.logger.error('Unable to retrieve log location for job execution {}\n{}'.format(job_execution, str(e)))

    def poll_job(self, resp, polling_interval=5):
        iteration = 1
        if 'items' in resp.keys() and len(resp['items']) == 1:
            resp = resp['items'][0]
        links = self.simplify_links(resp['links'])
        try:
            while resp['state'] == 'running':
                self.logger.debug('Polling job {} iteration #{}'.format(links['self'][-36:], iteration))
                time.sleep(polling_interval)
                resp = self.make_request('GET', links['self']).json()
                links = self.simplify_links(resp['links'])
                iteration += 1
            self.logger.info('Job: {} execution: {} will return logs at {}{}/content'.format(
                resp['jobRequest']['jobDefinition']['name'], links['self'][-36:], self.base_url, self.get_log_location(links['self'])))
            controller = '> /sso/sfw/ghusps-toolkit/toolkit_venv/bin/python ' \
                         '/sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_viya_functions.py -a {} ' \
                         '-d {}'.format(self.authfile, resp['id'])
            message = 'Job Request: {} Execution: {} {}. Logs can be found at link above or by invoking viya controller:\n' \
                      '{}'.format(resp['jobRequest']['id'], resp['id'], resp['state'], controller)
            if resp['state'] == 'completed':
                self.logger.info(message)
            elif resp['state'] == 'failed':
                self.logger.error(message)
            else:
                self.logger.warning('Job execution state unknown.')
            self.success = resp['state']
            return self.get_log_location(links['self'])
        except KeyError:
            self.logger.error('Job Execution ID appears invalid.')

    def simplify_links(self, links):
        try:
            return {link['rel']: link['href'] for link in links}
        except KeyError as e:
            self.logger.error('Provided links are not properly formatted\n{}'.format(str(e)))

    def get_log(self, job_execution):
        try:
            resp = self.make_request('GET', self.get_log_location(job_execution) + '/content')
            return resp
        except Exception as e:
            self.logger.error('Log could not be retrieved for job flow ID {}\n{}'.format(job_execution, str(e)))

    def run_job(self, job_id=None):
        endpoint = 'jobExecution/jobs'
        data = {'jobDefinitionUri': '/jobDefinitions/definitions/{}'.format(re.sub('["\']', '', job_id)),
                'arguments': {'_contextName': 'SAS Job Execution compute context'}}
        resp = self.make_request('POST', endpoint, json.dumps(data))
        try:
            return resp
        except Exception as e:
            self.logger.debug(resp)
            self.logger.error('Run job flow returned status code: {} and error {}'.format(resp.status_code, str(e)))

    def list_executions(self, user=None, uuid=None):
        resp = {}
        endpoint = 'jobExecution/jobs'
        if uuid is not None:
            endpoint += '?filter=eq(id,"{}")'.format(uuid)
        if user is not None and user:
            endpoint += '?filter=in(createdBy,{})'.format(','.join(user))
        try:
            resp = self.make_request('GET', endpoint).json()
            return resp
        except ValueError or TypeError as e:
            self.logger.warning('List executions response could not be cooerced to json.\n{}\n{}'.format(resp, e))
        except Exception as e:
            self.logger.error('Unable to make request to list executions at endpoint: {}\n{}'.format(endpoint, str(e)))

    def list_jobs(self, user=None, uuid=None):
        endpoint = 'jobDefinitions/definitions'
        if uuid is not None:
            endpoint += '?filter=eq(id,"{}")'.format(uuid)
        if user is not None and user:
            endpoint += '?filter=in(createdBy,{})'.format(','.join(user))
        try:
            resp = self.make_request('GET', endpoint).json()
            return resp
        except ValueError or TypeError as e:
            self.logger.warning('List jobs response could not be coerced to json.\n{}\n{}'.format(resp, e))
        except Exception as e:
            self.logger.error('Unable to make request to list jobs at endpoint: {}\n{}'.format(endpoint, str(e)))

    def list_flow_job(self, uuid=None):
        resp = None
        endpoint = 'jobFlowScheduling/jobs/{}'.format(uuid)
        try:
            resp = self.make_request('GET', endpoint).json()
            return resp
        except ValueError or TypeError as e:
            self.logger.warning('List flow job response could not be coerced to json.\n{}\n{}'.format(resp, e))
        except Exception as e:
            self.logger.error('Unable to make request to list flow job at endpoint: {}\n{}'.format(endpoint, str(e)))

    def list_flows(self, user=None, uuid=None):
        resp = None
        endpoint = 'jobFlowScheduling/flows'

        # filter=or(eq(id, 'X'), eq(id, 'Y'))
        if uuid is not None:
            if ',' not in str(uuid):
                endpoint += '?filter=eq(id, "{}")'.format(uuid)
            else:
                did_first = False
                endpoint += '?filter=or('
                for id in str(uuid).split(','):
                    if not did_first:
                        did_first = True
                    else:
                        endpoint += ','
                    endpoint += 'eq(id, "{}")'.format(id)
                endpoint += ')'

        if user is not None and user:
            if type(user) == list:
                user = user[0]
            print('user=<{}>').format(user)
            endpoint += "?filter=and(eq(createdBy,'{}'),eq(triggerType,'event'))".format(user)
        try:
            resp = self.make_request('GET', endpoint).json()
            return resp
        except ValueError or TypeError as e:
            self.logger.warning('List flows response could not be coerced to json.\n{}\n{}'.format(resp, e))
        except Exception as e:
            self.logger.error('Unable to make request to list flows at endpoint: {}\n{}'.format(endpoint, str(e)))

    def create_job(self, job):
        endpoint = 'jobDefinitions/definitions'
        try:
            resp = self.make_request('POST', endpoint, data=json.dumps(job)).json()
            return resp
        except Exception as e:
            self.logger.error('Unable to create_job')
            raise e

    def make_request(self, request_type='GET', endpoint=None, data=None):
        print('Making HTTP {} request to {}').format(request_type, endpoint)
        url = '{}/{}'.format(self.base_url, endpoint)
        try:
            if request_type == 'GET':
                if self.limit.search(url) is None:
                    url += '?'
                else:
                    url += '&'
                url += 'limit=200'
                resp = self.session.get(url)
            elif request_type == 'POST':
                resp = self.session.post(url, data)
            elif request_type == 'PUT':
                resp = self.session.put(url, data)
            elif request_type == 'DELETE':
                resp = self.session.delete(url)
            elif request_type == 'PATCH':
                resp = self.session.patch(url, data)
            elif request_type == 'OPTIONS':
                resp = self.session.options(url).headers['allow']
            elif request_type == 'HEAD':
                resp = self.session.head(url).headers
            else:
                raise AMSException('Request request_type {} not supported'.format(request_type))
            return resp
        except Exception as e:
            self.logger.error('{} request failed at endpoint {}'.format(request_type, endpoint))

    def _generate_token(self, retry=None):
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'Accept': 'application/json'}
        data = {'grant_type': 'client_credentials'}
        url = '{}/SASLogon/oauth/token'.format(self.base_url)
        try:
            r = requests.post(url=url, headers=headers, data=data, auth=(self.client_id, self.client_secret))
            if r.status_code == 200:
                self.access_token = r.json()['access_token']
                self.session.headers = {'Content-Type': 'application/json',
                                        'Accept': 'application/json',
                                        'Authorization': 'Bearer {}'.format(self.access_token)}
            elif retry is None:
                self._generate_token(retry=False)
            else:
                raise AMSException('Access token was not generated.')
        except Exception as e:
            raise e

    def _load_auth(self, authfile, profile):
        self.logger.debug('Loading authentication for profile [{}] from {}'.format(profile, authfile))
        config = ConfigParser.RawConfigParser()
        try:
            if len(config.read(authfile)) == 0:
                # ConfigParser.read() fails silently if no files found
                raise AMSException('Invalid or missing auth file {}'.format(authfile))
        except Exception as e:
            self.logger.error('The specified auth file [{}] does not appear to be properly formatted.'.format(
                authfile))
            raise e

        # Inefficient but sections should be small and I cannot think of another way to compensate for case.
        for section in config.sections():
            if profile.upper() == section.upper() and profile != section:
                self.logger.info('Profile case mismatch, using config section [{}] instead of provided profile '
                                 '[{}]'.format(section, profile))
                profile = section

        if profile in config.sections():
            options = config.options(profile)
            if sorted(options) == ['base_url', 'client_id', 'client_secret']:
                self.base_url = config.get(profile, 'base_url')
                self.client_id = config.get(profile, 'client_id')
                self.client_secret = config.get(profile, 'client_secret')
                self.logger.debug('Authentication profile loaded successfully.')
            else:
                self.logger.error('Auth file does not appear to be properly formatted, it should contain:\n'
                                  '[PROFILE]/n'
                                  'base_url: <https://VIYA_URL>\n'
                                  'client_id: <CLIENT_ID>\n'
                                  'client_secret: <CLIENT_SECRET>')
                raise
        else:
            self.logger.error('Profile [{}] not found.'.format(profile))
            raise AMSException('Unable to load auth from file {}'.format(authfile))
