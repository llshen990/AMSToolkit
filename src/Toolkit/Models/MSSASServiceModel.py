__author__ = "Scott Greenberg"
__email__ = "scott.greenberg@sas.com"

import os
from Toolkit.Lib.Helpers.MSSsh import MSSsh
from re import findall, search
from socket import gethostname
from ast import literal_eval


class MSSASServiceModel:

    def __init__(self, lev1='/sso/biconfig/940/Lev1'):
        """
        :param Lev1: Path to the Lev1 directory, default /sso/biconfig/940/Lev1
        """
        # instructions.html filepath
        self.inst_filepath = os.path.join(lev1, 'Documents', 'Instructions.html')
        self.sas_servers_path = os.path.join(lev1, 'sas.servers')
        self.lev1 = lev1

    # duplicate from MSSasServiceConnectorCommandLineView, but necessary to avoid circular import
    @staticmethod
    def color_format(text, color):
        begin = ''
        if color == 'red':
            begin = '\033[0;91m'
        elif color == 'green':
            begin = '\033[0;92m'
        elif color == 'blue':
            begin = '\033[0;94m'
        end = '\033[0m'
        return begin + str(text) + end

    def get_distro(self, hostname=None):
        """
        checks what linux distro is installed
        :param hostname:
        :return str:
        """
        valid_kernels = ['redhat', 'oracle']
        release_dirs = MSSsh.runcmd('ls /etc', hostname).std_out
        # release file of the installed kernel
        kernel_release = [k for k in release_dirs.split('\n') if any(v in k for v in valid_kernels)][0]
        return MSSsh.runcmd('cat /etc/{}'.format(kernel_release), hostname).std_out

    def get_kernel_name(self, hostname=None):
        """
        get the name of the installed linux kernel
        :param hostname:
        :return str:
        """
        return MSSsh.runcmd('uname', hostname).std_out

    def get_kernel_version(self, hostname=None):
        """
        get the version of the installed linux kernel
        :param hostname:
        :return str:
        """
        return MSSsh.runcmd('uname -r', hostname).std_out

    def get_uptime(self, hostname=None):
        """
        get uptime of server
        :param hostname:
        :return tuple: (uptime, users, load_avg)
        """
        # results of uptime command before parsing
        raw_uptime = MSSsh.runcmd('uptime', hostname).std_out
        uptime_split = raw_uptime.split(',', 2)
        uptime = uptime_split[0].split(' ', 1)
        uptime = uptime[len(uptime)-1]
        users = uptime_split[1].strip().split(' ')[0]
        load_avg = uptime_split[2]
        # we just want the numbers
        load_avg = load_avg.split(':')[1].split(',')
        load_avg = ''.join([
            load_avg[0] + ' (1m)',
            load_avg[1] + ' (5m)',
            # last entry has a \n
            load_avg[2].rstrip() + ' (15m)'
        ])
        return uptime, users, load_avg

    def get_cpu_info(self, hostname=None):
        """
        get cpu info for the given hostname,
        used to pass to MSSasServiceConnectorCommandLineView.print_cpu()
        :param hostname:
        :return tuple: (cpu_name, cpu_cores)
        """
        cpu_results = MSSsh.runcmd('cat /proc/cpuinfo', hostname).std_out
        cpu_name = search(r'\nmodel name.*\n', cpu_results).group(0)
        # get rid of extra whitespace and carriage returns
        cpu_name = ' '.join(cpu_name.split()).rstrip().split(':')[1][1:]
        # number of cores we have
        cpu_cores = len(findall('processor', cpu_results[0]))
        return cpu_name, cpu_cores

    def get_sas_services_status(self, hostname=None):
        """
        get status of sas services/servers
        :param hostname:
        :return str:
        """
        try:
            return MSSsh.runcmd(self.sas_servers_path + ' status', hostname).std_out
        except OSError:
            return 'Please ensure that this system has SAS installed.'

    def get_sudo_access_status(self, hostname=None):
        """
        check if sudo access is available, this is a simple check so we just need the return code
        :param hostname:
        :return str:
        """
        return MSSsh.runcmd('sudo -V', hostname).returncode

    def get_sas_app_urls(self, instructions_html):
        """
        returns list of urls for installed sas apps for environment
        :param str instructions_html: expected input is from a $ cat <instructions.html>
        :return list: return_urls
        """
        # set to get rid of duplicates
        urls = set(findall(r'http://[A-Za-z0-9/.]*.vsp.sas.com:[0-9/.]*/[A-Za-z0-9/?&_=.]*', instructions_html))
        # we have to do this because no set literals in python 2.6
        return [l for l in urls]

    def check_urls(self, urls):
        """
        does a sas-check on every url in list and returns list of results
        :param list urls: list of urls for installed sas apps from get_sas_app_urls()
        :return list: list of tuples of url, results of sas-check (from ops.tar) on url
        """
        results = []
        sas_check_path = os.path.abspath(os.path.join(os.path.realpath(__file__), os.pardir))
        sas_check_path = os.path.join(os.path.join(sas_check_path, os.pardir), 'ops-infrastructure', 'sas-check')
        for u in urls:
            test = None
            try:
                http_cmd = [sas_check_path,
                            'http',
                            '-meth',
                            'GET',
                            '-url',
                            u,
                            '-format',
                            'pretty']
                test = MSSsh.runcmd(http_cmd, gethostname())
            except OSError as ose:
                print ose
            test_dict = self.sas_check_result_to_dict(test)
            results.append((u, test_dict['message']))
        return results

    # converts results of sas-check (via runcmd) to a dict
    def sas_check_result_to_dict(self, result):
        # get rid of result code
        result = result.std_out
        # the 'if r' gets rid of blanks (''), join so we have a string
        result = ''.join([r.strip() for r in result.split('\n') if r])
        # convert string into dict literal
        return literal_eval(result)

    def get_webapp_status(self, instructions_html, midtier_hostname):
        """
        checks status of SAS webapp http(s) endpoints
        :param instructions_html: filepath to instructions.html file
        :param midtier_hostname:
        :return list of tuples: list of tuples consisting of url and success/error code:
        0 == pass, any other number is an http error code
        """
        # contains urls plus return codes
        final_results = []
        instructions_html = MSSsh.runcmd('cat ' + instructions_html, midtier_hostname).std_out
        urls = self.get_sas_app_urls(instructions_html)
        url_checks = self.check_urls(urls)
        # check for success/failures and append return codes
        for u in url_checks:
            url = u[0]
            output = u[1]
            http_return_code = 0
            if 'passed' not in output:
                # http status code if url check is a fail
                http_return_code = search(r'\d\d\d', output).group()
            final_results.append((url, http_return_code))
        return final_results

    def python_check(self, hostname=None):
        """
        :param hostname: hostname of machine to check
        :return str: python version
        """
        python_check_result = MSSsh.runcmd('python -V', hostname).std_err
        if python_check_result.startswith('Python'):
            version = python_check_result.split(' ')[1].strip()
            return version

    def init_scripts_check(self, required_init_scripts, hostname=None):
        """
        check if all expected sas init scripts are present
        :param hostname: hostname of machine to check
        :param required_init_scripts: list of init scripts required/expected by system
        :return bool or list: if fail then list missing init scripts
        """
        #TODO: this should include logic to check based on the role of the host
        init_script_check = MSSsh.runcmd('ls /etc/init.d', hostname).std_out
        # filter for sas scripts only
        init_script_check = [s for s in init_script_check if s.startswith('sas')]
        init_script_check_passed = all(i in required_init_scripts for i in init_script_check)
        if init_script_check_passed:
            return True
        else:
            return [i for i in required_init_scripts if i not in init_script_check]

    def sas_services_script_check(self, hostname=None):
        """
        check if sas.services script is in the proper location
        :return int: return code
        """
        return MSSsh.runcmd('ls -l ' + self.sas_servers_path, hostname).returncode

    def produce_report(
            self,
            midtier_hostname,
            instructions_html='/sso/biconfig/940/Lev1/Instructions.html',
            hostname=None,
            servers=None,
            verbose=False
        ):
        """
        produces MOTD-style report for given hostname
        :param midtier_hostname: this is needed for the url check
        :param instructions_html: path to Instructions.html file, can be overwritten
        :param hostname:
        :param servers: list of servers (to be used with verbose option)
        :param verbose: switch for printing in verbose mode
        :return dict: non-verbose: dict consisting of type(e.g. cpu):report/check
                      verbose: dict consisting of webapp report and list of server report dicts
                               of type(e.g. cpu):report/check
        """
        if verbose:
            report = {}
            # to account for servers that don't have an instructions file e.g. hadoop head nodes
            try:
                print(self.color_format('getting SAS Web App status', 'blue'))
                report['webapps'] = self.get_webapp_status(instructions_html, midtier_hostname)
            except OSError as ose:
                print(self.color_format(ose, 'red'))
            hostnames = servers.keys()
            server_reports = []
            for h in hostnames:
                report = {}
                report['hostname'] = h
                print(self.color_format(h + ': getting sudo status', 'blue'))
                report['sudo'] = self.get_sudo_access_status(h)
                print(self.color_format(h + ': getting python status', 'blue'))
                report['python'] = self.python_check(h)
                print(self.color_format(h + ': checking sas.services script location', 'blue'))
                report['sas_services_script'] = self.sas_services_script_check(h)
                print(self.color_format(h + ': getting sas.services status', 'blue'))
                report['sas_services'] = self.get_sas_services_status(h)
                server_reports.append(report)
            report['server_reports'] = server_reports
            return report
        else:
            report = {}
            # use localhost if hostname not provided
            report['hostname'] = hostname or gethostname()
            print(self.color_format('getting kernel info', 'blue'))
            report['distro'] = self.get_distro(hostname)
            report['kernel_name'] = self.get_kernel_name(hostname)
            report['kernel_version'] = self.get_kernel_version(hostname)
            print(self.color_format('getting uptime', 'blue'))
            report['uptime'] = self.get_uptime(hostname)
            print(self.color_format('getting cpu info', 'blue'))
            report['cpu'] = self.get_cpu_info(hostname)
            print(self.color_format('checking python installation', 'blue'))
            report['python'] = self.python_check(hostname)
            print(self.color_format('checking init scripts', 'blue'))
            report['init'] = self.init_scripts_check(list('sas.servers'), hostname)
            print(self.color_format('checking sas.services script location', 'blue'))
            report['sas_services_script'] = self.sas_services_script_check(hostname)
            print(self.color_format('getting sas.services status', 'blue'))
            report['sas_services'] = self.get_sas_services_status(hostname)
            # to account for servers that don't have an instructions file e.g. hadoop head nodes
            try:
                print(self.color_format('getting SAS Web App status', 'blue'))
                report['webapps'] = self.get_webapp_status(instructions_html, midtier_hostname)
            except OSError as ose:
                print(self.color_format(ose, 'red'))
            return report




