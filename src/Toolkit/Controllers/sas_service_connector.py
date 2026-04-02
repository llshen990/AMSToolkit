__author__ = "Scott Greenberg"
__email__ = "scott.greenberg@sas.com"

import argparse
import os
import sys
APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)
from Toolkit.Config.AMSEnvironment import AMSEnvironment
from Toolkit.Views.MSSasServiceConnectorCommandLineView import MSSasServiceConnectorCommandLineView

if __name__ == "__main__":

    arg_parser = argparse.ArgumentParser()

    # noinspection PyTypeChecker
    arg_parser.add_argument(
        "--config_file",
        nargs='?',
        type=str,
        help="path to config file",
        default='/sso/sfw/ghusps-toolkit/ssc/ssc_config.json'
    )

    arg_parser.add_argument('-l', '--Lev1', help='path to Lev1 on all tiers', dest='')
    arg_parser.add_argument('-v', '--verbose', help='displays complete output', action='store_true')
    args = arg_parser.parse_args()

    Lev1 = os.path.join('/', 'sso', 'biconfig', '940', 'Lev1')
    # overwrite Lev1 path if specified as arg
    try:
        if args.Lev1:
            Lev1 = args.Lev1
        elif args.l:
            Lev1 = args.l
        else:
            # default path to Lev1
            Lev1 = os.path.join('/', 'sso', 'biconfig', '940', 'Lev1')
    except AttributeError:
        pass

    ams_env = AMSEnvironment()

    instructions_html = os.path.join(Lev1, 'Documents', 'Instructions.html')
    servers = ams_env.create_server_dict(args.config_file)
    MSSAS_printer = MSSasServiceConnectorCommandLineView()
    midtier = ams_env.get_midtier_hostname(servers)

    # print data to console
    if args.verbose:
        MSSAS_printer.render(midtier, instructions_html, servers=servers, verbose=True)
    else:
        MSSAS_printer.render(midtier, instructions_html)

