#!/usr/bin/python

# @author owhoyt
# This file should be schedule in crontab to run ONE time per day.  It will write the number of days to the specified log file
# location without any grace periods factored in.  This is done so that Zabbix can monitor this and send out emails due to
# a defect in ECM where ECM does not honor the grace period.

import subprocess, re, os, traceback
from datetime import datetime

try:
    debug = False

    sas_exe = "/sso/sfw/sas/940/SASFoundation/9.4/sas"
    set_init_sas_program = "./setinit_info.sas"
    current_user = os.environ['USER']
    output_file = "/wmt/projects/fcs/" + current_user + "/run/signals/zabbix_batch_monitor/setinit_num_days_expire_no_grace.txt"

    p = subprocess.Popen([sas_exe, set_init_sas_program, "-stdio"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    setinit_listing, setinit_log = p.communicate()

    pattern = re.compile(".*Expiration:\s+([a-zA-Z0-9]+).*")
    expire_date_matches = pattern.findall(setinit_log)
    expire_date = expire_date_matches[0]

    fp = open(output_file, "w")

    if debug:
        print expire_date

    date_object = datetime.strptime(expire_date, '%d%b%Y')

    if debug:
        print date_object.date()

    expiry_date_delta = date_object - datetime.now()

    if debug:
        print expiry_date_delta

    num_days_until_expiry = expiry_date_delta.days

    if debug:
        print num_days_until_expiry

    fp.write(str(num_days_until_expiry))
    fp.close()
except Exception as e:
    print "Exception found: " + str(e)
    traceback.print_exc()
