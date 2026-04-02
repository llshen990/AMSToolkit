import os
import re
import json
import code
import argparse
import getpass
import shlex
import base64
import subprocess
import requests
import ConfigParser
import traceback
import readline # This gives us command history free in interactive mode

from Toolkit.Lib import AMSLogger
from Toolkit.Models import AMSViya


class ArgumentParser(argparse.ArgumentParser):
    # Override default behavior of print_help to prevent exit.
    def exit(self, status=0, message=None):
        if message is not None:
            print(message)
        pass


class AMSViyaFunctions:

    def __init__(self):
        self.authenticated = False
        self.args = parseargs()

        self.polling_interval = 5

        self.logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
        self.logger.set_debug(self.args.verbose)
        self.viya = None
        self.client_secret = None

    def login(self, args):
        try:
            self.viya = AMSViya(args.base_url, args.client_id, self.client_secret, args.authfile, args.profile, args.verbose)
            self.authenticated = True
        except Exception as e:
            self.logger.error('Unable to initialize connection.\n{}'.format(str(e)))
            if args.interactive:
                return 'Not Connected: '
            else:
                raise
        if args.interactive:
            if self.authenticated:
                return '{}\n{}: '.format(self.viya.base_url, self.args.profile)
            else:
                return 'Not Connected: '

    def _list_executions(self, identifiers):
        if len(identifiers) > 0 and len(identifiers[0]) == 36:
            resp = self.viya.list_executions(uuid=identifiers[0])
        else:
            resp = self.viya.list_executions(user=identifiers)
        if self.viya.verbose:
            self.viya.jprint(resp)
        elif 'count' in resp.keys() and resp['count'] > 0:
            if 'items' in resp.keys():
                executions = []
                for item in resp['items']:
                    try:
                        name = 'N/A'
                        if 'name' in item['jobRequest']['jobDefinition'].keys():
                            name = item['jobRequest']['jobDefinition']['name']
                        executions.append([item['creationTimeStamp'], name, item['id'], item['state']])
                    except Exception as e:
                        self.logger.error('The format of job execution was not as expected: {}'.format(item, str(e)))
            else:
                executions = [(resp['creationTimeStamp'], resp['jobRequest']['jobDefinition']['name'], resp['id'], resp['state'])]
            pad_time = 4 + max(len(timestamp) for timestamp, _, _, _ in executions)
            pad_name = 4 + max(len(name) for _, name, _, _ in executions)
            pad_exec = 4 + max(len(execution_id) for _, _, execution_id, _ in executions)
            for timestamp, name, execution_id, state in executions:
                print('Created: {}Name: {}ID: {}State: {}'.format(timestamp.ljust(pad_time), name.ljust(pad_name), execution_id.ljust(pad_exec), state))
        else:
            print('No executions found for: {}'.format(identifiers))

    def _list_jobs(self, identifiers):
        resp = self._get_jobs(identifiers)
        if not self.viya.verbose:
            if 'items' in resp.keys():
                jobs = [(item['name'], item['id']) for item in resp['items']]
            else:
                jobs = [(resp['name'], resp['id'])]
            if jobs is not None:
                padding = 4 + max(len(name) for name, _ in jobs)
                for name, jobid in jobs:
                    print('Name: {}ID: {}'.format(name.ljust(padding), jobid))
            else:
                print('No jobs found for: {}'.format(identifiers))
        else:
            self.viya.jprint(resp)

    def _list_flows(self, identifiers):
        resp = self._get_flows(identifiers)
        if not self.viya.verbose:
            if 'items' in resp.keys():
                jobs = [(item['name'], item['id']) for item in resp['items']]
                if jobs is not None:
                    padding = 4 + max(len(name) for name, _ in jobs)
                    for name, jobid in jobs:
                        print('Name: {}ID: {}'.format(name.ljust(padding), jobid))
            else:
                print('No jobs found for: {}'.format(identifiers))
        else:
            self.viya.jprint(resp)

    def _get_jobs(self, identifiers):
        if len(identifiers) > 0 and len(identifiers[0]) == 36:
            jobs = self.viya.list_jobs(uuid=identifiers[0])
        else:
            jobs = self.viya.list_jobs(user=identifiers)
        return jobs

    def _get_flows(self, identifiers):
        if len(identifiers) > 0 and len(identifiers[0]) == 36:
            jobs = self.viya.list_flows(uuid=identifiers[0])
        else:
            jobs = self.viya.list_flows(user=identifiers)
        return jobs

    def _run_job(self, uuid):
        resp = self.viya.run_job(uuid).json()
        if self.viya.verbose:
            self.viya.jprint(resp)
        self.logger.info('Polling interval is {}, sleeping for {} seconds. '
                         'Ctrl-C will not interrupt job only stop polling.'.format(self.polling_interval, self.polling_interval))
        try:
            self.viya.poll_job(resp, self.polling_interval)
        except Exception as e:
            self.logger.error('Unable to parse log link from run job request.\n{}'.format(str(e)))

    def _display_logs(self, uuid):
        log = self.viya.get_log(re.sub('["\']', '', uuid)).json()
        if self.viya.verbose:
            self.viya.jprint(log)
        else:
            print('\n'.join(['{}: {}'.format(item['type'], item['line']) for item in log['items']]))

    def _poll_job(self, uuid):
        self.viya.poll_job(self._get_execution(uuid))
        print('Job State: {}'.format(self.viya.success))

    def _get_execution(self, uuid):
        return self.viya.list_executions(uuid=uuid)

    def _get_errors(self, uuid):
        job = self._get_execution(uuid)['items'][0]
        if 'state' in job.keys() and job['state'] == 'failed' and 'error' in job.keys():
            self.viya.jprint(job['error'])
        else:
            self.logger.error('Successful jobs and jobs in progress do not have errors.')

    def _get_state(self, uuid):
        job = self._get_execution(uuid)['items'][0]
        if 'state' in job.keys():
            print('State: {}'.format(job['state']))
        else:
            self.logger.error('Job state is not defined for job {}'.format(uuid))

    def _export_job_definition(self, export_file, identifiers):
        try:
            with open(export_file, 'w+') as export:
                jobs = self._get_jobs(identifiers)
                if 'items' in jobs.keys():
                    json.dump(jobs['items'], export)
                else:
                    json.dump(jobs, export)
        except Exception as e:
            self.logger.error('Unable to export job definitions to {}\n{}'.format(export_file, str(e)))

    def _import_job_definition(self, import_file):
        status = []
        try:
            with open(import_file, 'r') as imp_file:
                jobs = json.load(imp_file)
            for job in jobs:
                resp = self.viya.create_job(job)
                if self.viya.verbose:
                    self.viya.jprint(resp)
                else:
                    status.append((resp['name'], resp['id']))
            if len(status) > 0:
                padding = 4 + max(len(name) for name, _ in status)
                for name, uuid in status:
                    print('Imported job: {}ID: {}'.format(name.ljust(padding), uuid))
        except Exception as e:
            self.logger.error('Failed to import jobs from file: {}\n{}'.format(import_file, str(e)))

    def _create_job_definition(self, job_file, parameters={}):
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
        actual_parameters = []
        try:
            if '_contextName' not in parameters.keys():
                parameters['_contextName'] = {'defaultValue': 'SAS Job Execution compute context',
                                              'type': 'CHARACTER', 'label': 'Context Name'}
            for name, values in parameters.items():
                tmp_values = values
                tmp_values.update({'name': name})
                actual_parameters.append(tmp_values)
            job_contents = {'parameters': actual_parameters,
                   'name': os.path.basename(job_file),
                   'type': 'Compute'}
        except Exception as e:
            self.logger.error('Unable to transform {} into a job definition\n{}'.format(job_file, str(e)))
        try:
            with open(job_file, 'r') as job_handle:
                job_contents['code'] = job_handle.read()
            job = self.viya.create_job(job_contents)
            self.logger.info('Job: {}\tCreated: {}\tUUID: {}'.format(job['name'], job['creationTimeStamp'], job['id']))
        except Exception as e:
            self.logger.error('Failed to create job definition with file: {}\n{}'.format(job_file, str(e)))

    def _passthrough(self, endpoint, verb, data):
        try:
            resp = self.viya.make_request(verb, re.sub('["\']', '', endpoint), data)
            if not hasattr(resp, 'status_code') or 200 <= resp.status_code < 300:
                try:
                    actual = resp.json()
                    self.viya.jprint(actual)
                except AttributeError:
                    actual = resp
                    try:
                        actual = dict(resp)
                        self.viya.jprint(actual)
                    except ValueError:
                        self.viya.jprint(actual)
                except Exception as e:
                    print(resp)
                    self.logger.debug("It's probably fine.\n{}".format(str(e)))
            else:
                self.logger.error('Passthrough request returned status {}\n'.format(resp.status_code, resp))
        except Exception as e:
            self.logger.error('Passthrough request failed.\n{}'.format(str(e)))

    def control(self, args):
        try:
            if args.list_jobs is not None:
                self._list_jobs(args.list_jobs)
            elif args.list_flows is not None:
                self._list_flows(args.list_flows)
            elif args.list_executions is not None:
                self._list_executions(args.list_executions)
            elif args.run is not None:
                self._run_job(args.run)
            elif args.display_logs is not None:
                self._display_logs(args.display_logs)
            elif args.poll_job is not None:
                self._poll_job(args.poll_job)
            elif args.error is not None:
                self._get_errors(args.error)
            elif args.state is not None:
                self._get_state(args.state)
            elif args.export_job_definition is not None:
                self._export_job_definition(args.export_job_definition, args.filter)
            elif args.import_job_definition is not None:
                self._import_job_definition(args.import_job_definition)
            elif args.create_job_definition is not None:
                self._create_job_definition(args.create_job_definition, args.parameters)
            elif args.passthrough is not None:
                self._passthrough(args.passthrough, args.type, args.data)
            elif args.help is not None:
                pass
            else:
                raise Exception('Function not supported')
        except AttributeError as e:
            if args.interactive:
                self.logger.warning('This functionality may require additional arguments only accessible in interactive mode.')
        except Exception as e:
            print(traceback.print_exc())
            self.logger.error('Unhandled exception encountered.\n{}'.format(str(e)))

    def write_config(self, args):
        config = ConfigParser.RawConfigParser()
        write = True
        if os.path.exists(args.create_auth_file):
            try:
                config.read(args.create_auth_file)
                if config.has_section(args.profile):
                    write_response = raw_input('Profile [{}] already exists, overwrite (Y)? '.format(args.profile)).lower()
                    write = True if write_response in ['y', 'yes'] else False
                else:
                    write = True
            except Exception as e:
                self.logger.error('Auth file ({}) exists but appears invalid.'.format(args.create_auth_file))
                raise e
        try:
            if write:
                if not config.has_section(args.profile):
                    if args.profile.upper() != 'DEFAULT':
                        config.add_section(args.profile)
                    else:
                        args.profile = args.profile.upper()
                config.set(args.profile, 'base_url', args.base_url)
                config.set(args.profile, 'client_id', args.client_id)
                config.set(args.profile, 'client_secret', self.client_secret)
                os.umask(0077)
                with open(args.create_auth_file, 'w+') as f:
                    config.write(f)
                self.logger.info('Profile [{}] has been written to {} use it to login with "-a {}"'.format(
                    args.profile, args.create_auth_file, args.create_auth_file))
        except Exception as e:
            self.logger.error('Unable to write profile [{}] to {}\n'.format(args.profile, args.create_auth_file, str(e)))

    def create_client(self, args):
        token_cmd = shlex.split('kubectl -n {} get secret sas-consul-client -o jsonpath="{{.data.CONSUL_TOKEN}}"'.format(args.namespace))
        try:
            client_token = base64.decodestring(subprocess.check_output(token_cmd))
        except Exception as e:
            self.logger.error('Unable to retrieve , ensure you are logged in via az cli')
            raise e
        try:
            self.viya = AMSViya(args.base_url, args.client_id, self.client_secret, args.authfile, args.profile, args.verbose, create=client_token)
            self.authenticated = True
        except Exception as e:
            self.logger.error('Client creation failed\n{}'.format(str(e)))


def parseargs(args=None):
    argparser = ArgumentParser()
    argparser.add_argument('-v', '--verbose', action='store_true', required=False,
                           help='Increase verbosity of commands, typically return full json output of rest call.')
    argparser.add_argument('-i', '--interactive', action='store_true', required=False,
                           help='Run functions interactively using single session')
    argparser.add_argument('-w', '--passthrough', type=str,
                           help='Convenience function to pass-through to rest API endpoint')
    argparser.add_argument('--data', type=str, help='Json data to passthrough to endpoint')
    argparser.add_argument('--type', choices=['GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'],
                           help='HTTP verb for passthrough request')

    create_group = argparser.add_argument_group('Create Authentication', 'Options for creating a new authentication type')
    create_group.add_argument('-u', '--create_client', action='store_true',
                              help='Create new client_id '
                                   '(requires active login for K8s cluster https://sas.service-now.com/kb?id=kb_article_view&sysparm_article=KB0029258)'
                                   'Used in interactive mode to create a new client_id/client_secret to be used for '
                                   'automations. Additional prompts will collect remaining required information.')
    create_group.add_argument('-f', '--create_auth_file', type=str, help='Once a client_id is created this provides a '
                                                                         'mechanism to actually use it.')
    create_group.add_argument('-m', '--create_profile', type=str, help='Create a new profile in an auth file')
    # create_group.add_argument('--auth_token', help='Create new auth token and refresh token')

    auth_group = argparser.add_argument_group('Authentication', 'Authentication options to use for session')
    auth_group.add_argument('-a', '--authfile', type=str, required=False,
                            help='Location of authfile containing "base_url", "client_id", and "client_secret", '
                                 'client expected to have "grant_type":"client_credentials"')
    auth_group.add_argument('-b', '--base_url', type=str, help='Baseurl for viya instance', required=False)
    auth_group.add_argument('-c', '--client_id', type=str, required=False,
                            help='If not using an auth file you can pass client_id as an argument, you will still be '
                                 'prompted separately for client_secret')
    auth_group.add_argument('-p', '--profile', type=str, default='Default', required=False,
                            help='Profile to use from authfile when authenticating (default: Default)')
    # auth_group.add_argument('-t', '--auth_token', action='store_true', nargs=2, help='Use auth token and refresh token')

    job_exec_group = argparser.add_argument_group('Job Executions', 'Options related to job executions')
    job_exec_group.add_argument('-d', '--display_logs', type=str, required=False,
                                help='Display the logs for a provided job execution UUID')
    job_exec_group.add_argument('-e', '--list_executions', type=str, nargs='*',
                                help='Without arguments lists all executions, with username(s) will attempt to find '
                                     'all job executions requested by specified user(s) (or client), with UUID(s) will '
                                     'return information about a specific job executions.')
    job_exec_group.add_argument('-o', '--poll_job', type=str,
                                help='For a given job execution poll state until state is no longer running and one of '
                                     '[complete, failed]')
    job_exec_group.add_argument('-s', '--state', type=str, help='Show state of job execution by UUID')
    job_exec_group.add_argument('-x', '--error', type=str,
                                help='Show errors for job execution by uuid (Null if job state is not failure)')

    # job_exec_group.add_argument('-z', '--ssl_cert_file', type=str, required=False, help='Path to SSL_CERT_FILE') # May not be necessary

    job_def_group = argparser.add_argument_group('Job Definitions', 'Options related to job definitions')
    job_def_group.add_argument('-l', '--list_jobs', type=str, required=False, nargs='*',
                               help='Without arguments list all jobs, with username(s) will attempt to find all job '
                                    'definitions created by specified user(s) (or client), with UUID(s) will return '
                                    'information about a specific job definition.')
    job_def_group.add_argument('--list_flows', type=str, required=False, nargs='*',
                               help='Without arguments list all jobs, with username(s) will attempt to find all job '
                                    'definitions created by specified user(s) (or client), with UUID(s) will return '
                                    'information about a specific job definition.')
    job_def_group.add_argument('-r', '--run', type=str, required=False, help='Run a job flow by UUID [RUN]')
    job_def_group.add_argument('-n', '--create_job_definition', type=str,
                               help='Create a new job definition from a local file, can be used in conjunction '
                                    'with --parameters')
    job_def_group.add_argument('--parameters', type=str, default='{}',
                               help='Parameters to be used in job definition [{"name": {"type": TYPE, "label": LABEL, '
                                    '"defaultValue": VALUE}}]')
    job_def_group.add_argument('-g', '--export_job_definition', type=str,
                               help='Export job definition(s) by uuid(s) or user(s) to a specified file.')
    job_def_group.add_argument('--filter', type=str, help='Limit export jobs to filter')
    job_def_group.add_argument('-k', '--import_job_definition', type=str,
                               help='Import job definition(s) in json format by uuid(s) or user(s) from a '
                                    'specified file.')

    if args is None:
        return argparser.parse_args()
    elif 'help' in args:
        argparser.print_help()
    else:
        return argparser.parse_args(args)


def main():
    functions = AMSViyaFunctions()
    args = functions.args

    if args.authfile is None and args.client_id is not None:
        functions.client_secret = getpass.getpass('client_secret: ')

    if args.authfile or args.client_id:
        prompt = functions.login(args)
    else:
        prompt = 'Not Connected: '

    if args.interactive:
        console = code.InteractiveConsole()
        while True:
            try:
                console_input = console.raw_input(prompt)
                if console_input.lower() in ['quit', 'bye', 'exit']:
                    exit(0)
                elif console_input:
                    try:
                        tmp_args = parseargs(console_input.split())
                        args = tmp_args if tmp_args is not None else args
                        if args.create_auth_file or args.create_profile:
                            if args.profile.upper() == 'DEFAULT':
                                tmp_profile = console.raw_input('Profile (Enter for Default): ')
                                args.profile = tmp_profile if tmp_profile else args.profile
                            args.base_url = console.raw_input('Base URL: ') if not args.base_url else args.base_url
                            args.client_id = console.raw_input('Client_ID: ') if not args.client_id else args.client_id
                            functions.client_secret = getpass.getpass('Client_Secret: ') if not functions.client_secret else functions.client_secret
                            functions.write_config(args)
                        elif args.create_client:
                            args.namespace = console.raw_input('Viya namespace: ')
                            args.base_url = console.raw_input('Base_URL: ') if not args.base_url else args.base_url
                            args.client_id = console.raw_input('Client_ID: ') if not args.client_id else args.client_id
                            functions.client_secret = getpass.getpass('Client_Secret: ') if not functions.client_secret else functions.client_secret
                            functions.create_client(args)
                            functions.login(args)
                        elif functions.authenticated:
                            if args.export_job_definition is not None:
                                args.filter = [console.raw_input('Export filter (can include uuids or names): ')]
                            if args.create_job_definition is not None:
                                parameters = {}
                                while True:
                                    parameter = console.raw_input('Parameter Name(Enter for none): ')
                                    if parameter != '':
                                        parameters[parameter] = {}
                                        for key in ['type', 'label', 'defaultValue']:
                                            value = console.raw_input('{} for {}: '.format(key, parameter))
                                            if value != '':
                                                parameters[parameter][key] = value
                                            else:
                                                print('Empty values not valid.')
                                    else:
                                        break
                                args.parameters = parameters
                            functions.control(args)
                        else:
                            print('Authentication required for most actions.')
                    except Exception as e:
                        functions.logger.error(str(e))
                        options()
            except KeyboardInterrupt:
                options()
            except EOFError:
                options()
    else:
        functions.control(args)


def options():
    print('\n"quit" and "help" are both valid commands.')


if __name__ == '__main__':
    main()
