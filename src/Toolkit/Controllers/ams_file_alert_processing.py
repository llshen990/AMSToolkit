#!/usr/bin/env python
# @author thraoz
import sys
import argparse
import logging
import traceback
import os

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Config import AMSConfig, AMSJibbixOptions, AMSAttributeMapper
from Toolkit.Models.AMSFileAlerting import AMSFileAlert
from Toolkit.Lib.Defaults import AMSDefaults


if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    ams_defaults = AMSDefaults()

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument('-s', "--source_path", nargs='?', type=str, help="provide full source file path", required=True)
    # noinspection PyTypeChecker
    arg_parser.add_argument('-d', "--destination_path", nargs='?', type=str, help="provide full destination file path", required=True)

    args = arg_parser.parse_args(sys.argv[1:])
    src_path = args.source_path.strip()
    dest_path = args.destination_path.strip()
    my_hostname_default = ams_defaults.my_hostname

    # AMSConfig class
    # what config is need actually
    ams_config = AMSConfig(
        src_path + '.json',
        # os.path.basename(src_filename_path) + ".json",
        allow_config_generation=False,
        always_new=True
    )

    try:
        # Model that does the parsing and loads jibbix options from json data
        alert_model = AMSFileAlert(ams_config, src_path, dest_path)
        if alert_model.check_destination_path():
            alert_model.load_to_jibbix()
        exit(0)
    except Exception as e:
        ams_defaults.my_hostname = my_hostname_default
        exception_str = "Exception while Parsing json or loading to jibbix {} ".format(str(e))
        exception_str += "Traceback: " + traceback.format_exc()
        ams_logger.error(exception_str)
        ams_attribute_mapper = AMSAttributeMapper()
        event_handler = ams_attribute_mapper.get_attribute('global_ams_event_handler')
        event_handler.zabbix.my_hostname = ams_defaults.my_hostname
        jibbix_options = ams_defaults.AMSJibbixOptions  # type: AMSJibbixOptions
        jibbix_options.labels = 'ams_toolkit, RMSS'
        jibbix_options.summary = '%s: RMSS Alert Processing Error | %s' % (ams_defaults.my_hostname, dest_path)
        jibbix_options.description = exception_str
        event_handler.create(jibbix_options)
        exit(0)