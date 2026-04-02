import re
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager

from Toolkit.Config.AMSConfig import AMSConfig
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from lib.Validators.FileExistsValidator import FileExistsValidator
from Toolkit.Exceptions.AMSException import AMSException


class AMSMobaXtermModel(AbstractAMSBase):
    def __init__(self):
        AbstractAMSBase.__init__(self, AMSConfig())
        self.counter = 1
        self.out_file = open('output.mxtsessions', 'wb')

    def __get_all_hosts(self, group):
        host_list = []
        host_list.extend(group.hosts)
        for child in group.child_groups:
            host_list.extend(self.__get_all_hosts(child))
        return host_list

    def __get_moba_string_by_host(self, variable_manager, host):
        vars = variable_manager.get_vars(host=host)
        if re.match('\w+ts\d.\.', host.name):
            return host.name + ' Terminal Server=#91#4%' + host.address + '%3389%default%0%-1%-1%-1%-1%0%0%-1%%%22%%-1%0%%-1#MobaFont%10%0%0%0%15%236,236,236%0,0,0%180,180,192%0%-1%0%%xterm%-1%0%0,0,0%54,54,54%255,96,96%255,128,128%96,255,96%128,255,128%255,255,54%255,255,128%96,96,255%128,128,255%255,54,255%255,128,255%54,255,255%128,255,255%236,236,236%255,255,255#0'

        if 'server_roles' in vars and vars['server_roles'] is not None:
            if 'cas_controller' in vars['server_roles'] and vars['server_roles']['cas_controller'] is True:
                    server_type = 'CAS Controller'
            elif 'cas_worker' in vars['server_roles'] and vars['server_roles']['cas_worker'] is True:
                server_type = 'CAS Controller'
            elif 'compute' in vars['server_roles'] and vars['server_roles']['compute'] is True and 'midtier' in vars['server_roles'] and vars['server_roles']['midtier'] is False:
                server_type = 'Compute'
            elif 'compute' in vars['server_roles'] and vars['server_roles']['compute'] is False and 'midtier' in vars['server_roles'] and vars['server_roles']['midtier'] is True:
                server_type = 'Midtier'
            elif 'compute' in vars['server_roles'] and vars['server_roles']['compute'] is True and 'midtier' in vars['server_roles'] and vars['server_roles']['midtier'] is True:
                server_type = 'App Server'
            else:
                server_type = 'Captain'
        else:
            server_type = 'Generic'

        if 'env' in vars:
            server_env = vars['env']
        else:
            server_env = 'Dev'

        return host.name+' '+server_env+' '+server_type+'= #109#0%'+host.address+'%22%<default>%%-1%-1%%%22%%0%0%Interactive shell%%%-1%0%0%0%%1080#MobaFont%10%0%0%0%15%236,236,236%0,0,0%180,180,192%0%-1%0%%xterm%-1%0%0,0,0%54,54,54%255,96,96%255,128,128%96,255,96%128,255,128%255,255,54%255,255,128%96,96,255%128,128,255%255,54,255%255,128,255%54,255,255%128,255,255%236,236,236%255,255,255#0'

    def generate_config(self, tla):
        # Checking for dynamic inventory
        base_directory = '/sso/eha/prod-inventory/'+tla
        if not FileExistsValidator.directory_readable(base_directory):
            raise AMSException('Dynamic inventory does not exist for TLA')

        # Get List of hosts
        inventory_file_name = base_directory
        data_loader = DataLoader()
        inventory = InventoryManager(loader=data_loader, sources=[inventory_file_name])
        variable_manager = VariableManager(loader=data_loader, inventory=inventory)

        host_map = {}
        root = inventory.groups[tla]  # Group
        product_list = root.child_groups

        self.out_file.write('[Bookmarks]\n')
        self.out_file.write('SubRep='+tla+'\n')
        self.out_file.write('ImgNum=41\n\n')
        for product in product_list:
            self.out_file.write('[Bookmarks_'+str(self.counter)+']\n')
            self.out_file.write('SubRep='+tla+'\\'+product.name+'\n')
            self.out_file.write('ImgNum=41\n')
            self.counter += 1
            environments = product.child_groups
            for environment in environments:
                self.out_file.write('\n')
                self.out_file.write('[Bookmarks_'+str(self.counter)+']\n')
                self.out_file.write('SubRep='+tla+'\\'+product.name+'\\'+environment.name+'\n')
                self.out_file.write('ImgNum=41\n')
                self.counter += 1
                host_map[environment.name] = self.__get_all_hosts(environment)
                hosts = host_map[environment.name]
                for host in host_map[environment.name]:
                    self.out_file.write(self.__get_moba_string_by_host(variable_manager, host)+'\n')
            self.out_file.write('\n')
