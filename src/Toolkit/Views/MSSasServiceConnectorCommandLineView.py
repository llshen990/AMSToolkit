__author__ = "Scott Greenberg"
__email__ = "scott.greenberg@sas.com"

from Toolkit.Models.MSSASServiceModel import MSSASServiceModel
from AbstractView import AbstractView
from socket import gethostname


class MSSasServiceConnectorCommandLineView(AbstractView):

    def __init__(self):
        AbstractView.__init__(self)
        self.__envcfg_red = '\033[0;91m'
        self.__envcfg_green = '\033[0;92m'
        self.__envcfg_blue = '\033[0;94m'
        self.__envcfg_no_color = '\033[0m'
        self.indent = ' ' * 5

    # Abstract methods (to be implemented later)

    def set_input_data(self, input_data):
        self.input_data = input_data

    def init(self):
        return

    # Formatting utilities

    def color_format(self, text, color):
        begin = ''
        if color == 'red':
            begin = self.__envcfg_red
        elif color == 'green':
            begin = self.__envcfg_green
        elif color == 'blue':
            begin = self.__envcfg_blue
        end = self.__envcfg_no_color
        return begin + str(text) + end

    @staticmethod
    def print_bar(self, name, perc, max, unit='B'):
        """
        prints motd style status bar for perf stats (e.g. cpu, swap, etc)
        :param name: name of metric to be displayed
        :param perc: percentage of metric used
        :param max: max number and unit of metric (i.e. the right side of the bar) (e.g. 23.8)
        :param unit: unit in which metric is measured, acceptable inputs are none(B), K, M, G, T
        """
        bar_length = 50
        # part of bar to color in, rounded up
        bar_colored = int(perc / 2)
        bar = '['
        # build bar
        bar += self.color_format('=', 'blue') * bar_colored
        bar += '=' * (bar_length - bar_colored)
        bar += ']'
        bar_text = str(perc) + '% used out of ' + str(max) + unit
        # space between name and end text, +1 for extra ] at end
        offset = ' ' * ((bar_length - (len(name) + len(bar_text))) + 1)
        # put the whole thing together + offset
        bar_text = name + offset + bar_text
        print(self.indent + bar_text)
        print(self.indent + bar)

    @staticmethod
    def columnize(text1, text2, col):
        """
        arranges two strings into a single string justified by column
        :param text1:
        :param text2:
        :param col: index where column for text2 begins
        :return: single string with text2 justified by col
        """
        offset = ' ' * (col - len(text1))
        return text1 + offset + text2

    def print_generic_check(self, name, return_code):
        if return_code == 0:
            print(name + ' ' + self.color_format('PASS', 'green'))
        elif return_code != 0:
            print(name + ' ' + self.color_format('FAIL', 'red'))

    def print_hostname(self):
        """
        prints hostname of the system running the motd check
        """
        print('Hostname: ' + gethostname() + '\n')

    def print_uptime(self, uptime_results):
        """
        prints uptime, users, and load average
        :param uptime_results: results from MSSASServiceModel.get_uptime()
        :return:
        """
        uptime, users, load_avg = uptime_results[0], uptime_results[1], uptime_results[2]
        # print everything
        print(self.indent + 'Uptime......: ' + uptime)
        # weird formatting, but gets the job done
        print(self.indent + 'Users.......: ' + users)
        print(self.indent + 'Load........: ' + load_avg + '\n')

    def print_cpu(self, cpu_results):
        """
        :param cpu_results: results from MSSASServiceModel.get_cpu_info()
        """
        cpu_name, cpu_cores = cpu_results[0], cpu_results[1]
        print(
                self.indent +
                'CPU.........: ' +
                cpu_name +
                ' ' +
                '(' +
                str(cpu_cores) +
                ' cores)' +
                '\n'
        )

    def print_python_version(self, python_check_result):
        """
        :param python_check_result: result from MSSASServiceModel.get_python_version()
        """
        # if python is not installed this will be None
        if python_check_result:
            print('Python Version: ' + self.color_format(python_check_result, 'green'))
        else:
            print(self.color_format('PYTHON NOT INSTALLED', 'red'))

    def print_init_scripts(self, init_script_result):
        """
        prints whether sas init scripts are present
        :param init_script_result: result from MSSASServiceModel.get_sas_init_scripts()
        """
        if init_script_result == True:
            print('SAS Init Scripts' + ' ' + self.color_format('PASS', 'green'))
        else:
            print(self.color_format('SAS Init Scripts Missing: ', 'red') + ' '.join(init_script_result))

    def print_sudo_access(self, sudo_check_result):
        """
        :param sudo_check_result: result from MSSASServiceModel.get_sudo_access_status()
        """
        self.print_generic_check('Sudo Access', sudo_check_result)

    def print_distro(self, distro, kernel_name, kernel_version):
        """
        :param distro: result from MSSASServiceModel.get_distro()
        :param kernel_name: result from MSSASServiceModel.get_kernel_name()
        :param kernel_version: result from MSSASServiceModel.get_kernel_version()
        """
        print('System Info:')
        # rstrip to get rid of newlines
        print(self.indent + 'Distro......: ' + distro.rstrip())
        print(self.indent + 'Kernel......: ' + kernel_name.rstrip() + ' ' + kernel_version)

    def print_webapps_status(self, results):
        """
        :param results: results from MSSASServiceModel.url_check()
        """
        print('Web App Status:')
        if not results:
            print(self.color_format('NO SAS APPS FOUND', 'red'))
        else:
            for r in results:
                    url = r[0]
                    return_code = r[1]
                    # if url check is a success
                    if return_code == 0:
                        print(self.indent + url + ' ' + self.color_format('PASS', 'green'))
                    # if url check is a fail
                    else:
                        # http status code if url check is a fail
                        print(self.indent + url + ' ' + self.color_format(
                            'FAIL: ' + return_code + ' error', 'red'
                        ))

    def print_sas_services(self, results):
        """
        prints status of sas services from sas.services status
        :param results: results of MSSASServiceModel.get_sas_services_status()
        :return:
        """
        print('SAS Services: ')
        # this is so we can print two at a time
        status1 = ''
        status2 = ''
        # remove lines that aren't X is UP||not UP
        results = [r for r in results.split('\n') if 'is' in r]
        for r in results:
            is_last_result = results.index(r) == len(results)
            name = r.split('is')[0].strip()
            status = r.split('is')[1]
            if 'NOT' in status:
                status = self.color_format('DOWN', 'red')
            elif 'UP' in status:
                status = self.color_format('UP', 'green')
            status_text = name + ' ' + status
            # control flow for printing multiple on one line
            if not status1:
                status1 = status_text
            elif not status2:
                # right justify text
                status2 = status_text
            # print the last result if we have an odd number of results
            if status1 and is_last_result:
                print(self.indent + status1)
            # ready to print
            if status1 and status2:
                print(self.indent + self.columnize(status1, status2, 55))
                status1, status2 = '', ''

    def print_sas_services_script(self, results):
        """
        prints whether sas.services script is in expected location
        :param results: results of MSSASServiceModel.get_sas_services_status()
        :return:
        """
        if results == 0:
            print('sas.services script found in expected location')
        else:
            print(self.color_format('sas.services script not found', 'red'))

    def get_data(
            self,
            midtier_hostname,
            instructions_html='/sso/biconfig/940/Lev1/Instructions.html',
            hostname=None,
            servers=None,
            verbose=False
        ):
        """
        get system report from model
        :param midtier_hostname:
        :param instructions_html: path to instructions.html file on midtier
        :param hostname: hostname
        :param servers: list of servers (to be used with verbose option)
        :param verbose: switch for printing in verbose mode
        :return dict: system report or dict of system reports (for verbose mode)
        """
        model = MSSASServiceModel()
        return model.produce_report(
            midtier_hostname,
            instructions_html,
            hostname=hostname,
            servers=servers,
            verbose=verbose
        )

    def render(self, midtier_hostname, instructions_html, hostname=None, servers=None, verbose=False):
        """
        print short MOTD-style report of system info
        :param report: report generated by MSSASServiceModel.generate_report()
        :param verbose: print verbose report of system info ala sasenvctl status
        :param servers: list of servers to be used with verbose option
        """
        report = self.get_data(midtier_hostname, instructions_html, hostname, servers, verbose)
        if verbose:
            try:
                self.print_webapps_status(report['webapps'])
            except KeyError:
                print(self.color_format('sas webapps not found', 'red'))
            for s in report['server_reports']:
                print('*' * 10)
                print(s['hostname'])
                self.print_sudo_access(s['sudo'])
                self.print_python_version(s['python'])
                self.print_sas_services_script(s['sas_services_script'])
                self.print_sas_services(s['sas_services'])
                print('*' * 10)
        else:
            print('\n' + report['hostname'] + '\n')
            self.print_uptime(report['uptime'])
            self.print_cpu(report['cpu'])
            self.print_distro(report['distro'], report['kernel_name'], report['kernel_version'])
            self.print_init_scripts(report['init'])
            self.print_python_version(report['python'])
            self.print_sas_services_script(report['sas_services_script'])
            self.print_sas_services(report['sas_services'])
            try:
                self.print_webapps_status(report['webapps'])
            except KeyError:
                print(self.color_format('sas webapps not found', 'red'))

