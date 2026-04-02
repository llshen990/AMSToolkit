from collections import OrderedDict
import os
import argparse

# APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
# sys.path.append(APP_PATH)

def main(ini_in_file_path, ini_out_file_path):
    """
    :param ini_in_file_path: full path of input INI file
    :type ini_in_file_path: str
    :param ini_out_file_path: full path of output (reformatted) INI file
    :type ini_out_file_path: str
    :return: True on success, exception on failure.
    :rtype: bool
    """

    services = _read_ini_in_file_path(ini_in_file_path)
    _write_ini_file_path_out(ini_out_file_path, services)

    return True

def _read_ini_in_file_path(ini_in_file_path):
    """
    This method will set the orig_log_file_path variable for the schedule.  This is an optional override.
    :param ini_in_file_path: full path of input INI file
    :type ini_in_file_path: str
    :return: services = OrderedDict()
    :rtype: services
    """
    first_service = False
    services = OrderedDict()
    services['unassigned'] = {
        'full_target': 'Unassigned Services',
        'services': []
    }
    current_service = None
    all_children = []
    service_assigned = False

    # with open('./inventory_in.ini', 'rU') as f:
    with open(ini_in_file_path, 'rU') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                continue
            if not first_service:
                if line.startswith('deployTarget'):
                    target_parts = line.split(' ')
                    services[target_parts[0]] = {
                        'full_target': line,
                        'services': []
                    }
                elif line.startswith('worker'):
                    worker_parts = line.split(' ')
                    services[worker_parts[0]] = {
                        'full_target': line,
                        'services': []
                    }
                elif line.startswith('['):
                    first_service = True
            if first_service and current_service != '':
                if line.startswith('[') and current_service != line:
                    if not service_assigned and current_service:
                        services['unassigned']['services'].append(current_service)
                    service_assigned = False
                    current_service = line  # type: str
                elif current_service == '[sas-all:children]':
                    all_children.append(line)
                else:
                    services[line]['services'].append(current_service)
                    service_assigned = True
    return services

def _write_ini_file_path_out(ini_out_file_path, services):
    """
    This method will set the orig_log_file_path variable for the schedule.  This is an optional override.
    :param ini_out_file_path: full path of output (reformatted) INI file
    :type ini_out_file_path: str
    :param services = OrderedDict()
    :type services = OrderedDict()
    :return: True upon success or False upon failure.
    :rtype: bool
    """

    output_file = open(ini_out_file_path, "w+")
    for target, target_data in services.iteritems():
        output_file.write(target_data['full_target'] + os.linesep)
        if len(target_data['services']) > 0:
            for service in target_data['services']:
                output_file.write(service + os.linesep)
        output_file.write(os.linesep)
    output_file.close()
    return True

# this is how we invoke the main method to start everything off and we pass in argv from sys.
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", nargs='?', type=str, help="Path to the input inventory .ini file", required=True)
    parser.add_argument("--output_file", nargs='?', type=str, help="Path to the reformatted output inventory .ini file", required=True)
    args = parser.parse_args()
    main(args.input_file, args.output_file)