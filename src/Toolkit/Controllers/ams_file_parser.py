from __future__ import print_function
import os
import re
import sys
import argparse

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Lib.Defaults import AMSDefaults
from Toolkit.Config import AMSConfig
from Toolkit.Exceptions import AMSException, AMSConfigException
from Toolkit.Models.AMSFileParser import AMSFileParserModel
from Toolkit.Lib.Helpers import ProcCheck


def get_config(config_file):
    try:
        tmp_config = AMSConfig(config_file)
    except Exception:
        tmp_config = AMSConfig()
    return tmp_config


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-c', '--config_file', nargs='?', type=str, help='Config File', required=True)
    arg_parser.add_argument('-p', '--file_parser', nargs='?', type=str, help='Name of file parser to execute', required=True)

    args = arg_parser.parse_args()

    # Don't remove me, I promise I'm actually necessary
    ams_defaults = AMSDefaults()

    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '-' + re.sub(r' |' + os.sep, '_', args.file_parser))
    ams_config = get_config(args.config_file)

    ams_logger.set_debug(ams_config.debug)

    if not ams_config.valid_config:
        raise AMSConfigException('Invalid configuration file specified: {}'.format(args.config_file))

    ams_file_parser = AMSFileParserModel(ams_config, args.file_parser)

    proc_check = None
    tmp_file_parser = str(args.file_parser).strip()
    if not tmp_file_parser or tmp_file_parser is None:
        tmp_file_parser = 'unknown_file_parser'

    try:
        proc_check = ProcCheck(controller_name=__file__, context=tmp_file_parser, lock_dir='/tmp')
        # initiate the proc check.
        ams_logger.info('Running check on lock file {}'.format(proc_check.lock_file_name))
        if not proc_check.lock():
            raise Exception('File parser {} is currently locked. Please check the process and {} file as needed'.format(tmp_file_parser, proc_check.lock_file_name))

        ams_file_parser.execute_file_parser()
    except KeyError:
        message = 'The named file parser: "{}" does not exist in the specified config: "{}"'.format(args.file_parser, args.config_file)
        ams_logger.error('The named file parser: "{}" does not exist in the specified config: "{}"'.format(args.file_parser, args.config_file))
        raise AMSConfigException(message)
    except Exception as e:
        message = 'File Parser "{}" failed to execute.\n{}'.format(args.file_parser, e)
        ams_logger.critical(message)
        raise AMSException(message)
    finally:
        # Remove lock file
        if proc_check:
            proc_check.unlock()


if __name__ == '__main__':
    main()

