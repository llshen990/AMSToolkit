import os
import sys
import argparse
import logging
import traceback
import csv

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Exceptions import AMSConfigException
from Toolkit.Config import AMSWebScenario
from lib.Validators import FileExistsValidator
from Toolkit.Models import AMSStpPhaseOneConfigCreator

if __name__ == "__main__":

    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    ams_logger.set_debug(True)

    arg_parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    arg_parser.add_argument("--csv_file", nargs='?', help="CSV File to generate configs from", required=True)
    arg_parser.add_argument("--output_folder", nargs='?', help="Output folder to store config files", required=True)

    args = arg_parser.parse_args(sys.argv[1:])
    # ams_logger.debug('csv_file=%s' % str(args.config_file).strip())
    csv_file_path = args.csv_file.strip()
    output_folder = args.output_folder.strip()

    failed_validations = False
    fev = FileExistsValidator(True)
    if not fev.validate(csv_file_path):
        failed_validations = True

    if not fev.directory_writeable(output_folder):
        failed_validations = True

    if failed_validations:
        print fev.format_errors()
        exit()

    try:
        with open(csv_file_path, 'r') as csv_file:
            # loop through line by line of csv file
            readCSV = csv.reader(csv_file, delimiter=',')
            for row in readCSV:
                app = row[0].strip()

                if 'app service' in app.lower() or 'app_service' in app.lower():
                    ams_logger.debug('Skipping header row')
                    continue

                base_url = row[1].strip()
                check_type = row[2].strip()
                tla = row[3].strip()
                port = row[4].strip()
                sas_login = int(row[5].strip())
                sas_studio = int(row[6].strip())
                sas_stored_process = int(row[7].strip())
                sas_web_report_studio = int(row[8].strip())
                sas_wip_services = int(row[9].strip())
                sas_version = row[10].strip()

                # if app not in ['TEST_ITM_APP']:
                #     continue

                url_and_port = 'http://' + base_url + ':' + port
                ams_logger.debug('Creating config for app: %s on baseurl: %s' % (app, url_and_port))
                configGen = AMSStpPhaseOneConfigCreator(app, base_url, output_folder)
                # If type is MI then we add MI health check to config
                if check_type.lower() in ['mi']:
                    configGen.add_mi_healthcheck(url_and_port)

                    ams_web_scenario = AMSWebScenario()
                    configGen.add_web_scenarios(ams_web_scenario)

                    if sas_login:
                        configGen.create_web_scenario_step(ams_web_scenario, "SAS Logon", url_and_port, check_type)

                    # add web scenarios for all 7 endpoints
                    # configGen.create_web_scenario_step(ams_web_scenario, "Visual Analytics", url_and_port, check_type)
                    if sas_studio:
                        configGen.create_web_scenario_step(ams_web_scenario, "SAS Studio", url_and_port, check_type)
                    # configGen.create_web_scenario_step(ams_web_scenario, "SAS SNA", url_and_port, check_type)
                    # configGen.create_web_scenario_step(ams_web_scenario, "SAS Portal", url_and_port, check_type)
                    if sas_web_report_studio:
                        configGen.create_web_scenario_step(ams_web_scenario, "SAS Web Report Studio", url_and_port, check_type)

                    if sas_stored_process:
                        configGen.create_web_scenario_step(ams_web_scenario, "SAS Stored Process", url_and_port, check_type)

                    if sas_wip_services:
                        configGen.create_web_scenario_step(ams_web_scenario, "SAS WIP Services", url_and_port, check_type)
                else:
                    ams_logger.critical('This config generator is only for Merchandise Intelligence (MI)')

                configGen.write_config()

    except KeyboardInterrupt:
        print '%sUser termination.  Exiting...' % os.linesep
    except AMSConfigException as e:
        print 'Config exception occurred: ' + str(e)
    except Exception as e:
        ams_logger.error("Caught an exception: " + str(e))
        ams_logger.error("Traceback: " + traceback.format_exc())
        raise