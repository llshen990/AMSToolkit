import os
import sys
import argparse
import logging
import subprocess

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Lib import AMSLogger
from Toolkit.Config import AMSJibbixOptions
from Toolkit.Lib.Helpers import AMSZabbix
from Toolkit.Lib.Defaults import AMSDefaults

def create_sas(file_name):
    sas_file = open(file_name, "w+")
    sas_file.write("proc sql; \n")
    sas_file.write("CREATE TABLE WORK.partitions AS \n")
    sas_file.write("SELECT PROD_HIER_SK \n")
    sas_file.write("FROM di_trans.tkmi_grid_data_map \n")
    sas_file.write("ORDER BY PROD_HIER_SK; \n")
    sas_file.write("quit;\n\n")

    sas_file.write("proc export DATA=work.partitions \n ")
    sas_file.write(" OUTFILE='/sso/sfw/LoadMgr/adhoc/partitions.txt' \n")
    sas_file.wrtie(" DBMS=DLM REPLACE; \n")
    sas_file.write(" PUTNAMES=NO; \n")
    sas_file.write("RUN;")

    sas_file.close()

def execute_sas(file_name):
    try:

        result = subprocess.call(["/sso/biconfig/930/Lev1/MIMain/Batch/sas_batch.sh", "-nodms", "-LOG",
                                  "/amk/warehouse/backup/test/verify1.log", "-PRINT",
                                  "/amk/warehouse/backup/test/verify1.lst", "/amk/warehouse/backup/test/verify.sas"])
        print result
    except IOError as e:
        print e


if __name__ == "__main__":
    ams_logger = AMSLogger(log_filename=os.path.basename(__file__) + '.log')
    AMSDefaults = AMSDefaults()

    partition_dir = "/sca/warehouse/default/marts/dm/1"

    for part_folder in sorted(os.listdir(partition_dir)):
        if os.path.isdir(os.path.join(os.path.abspath(partition_dir), part_folder)):
            if part_folder != "0":
                print part_folder
