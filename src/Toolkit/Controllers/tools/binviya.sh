#!/usr/bin/env bash
# Wrapper for sked to dynamically create job definitions from SAS code on demand and run them.
#set -x
CONTROLLER="/sso/sfw/ghusps-toolkit/toolkit_venv/bin/python /sso/sfw/ghusps-toolkit/ams-toolkit/src/Toolkit/Controllers/ams_viya_functions.py"
AUTH_FILE="/home/vagrant/.auth"

filename=$1

CREATE_JOB=$($CONTROLLER -a "$AUTH_FILE" -n "$filename")
JOB_ID=$(tail -n1 <(printf "%s" "$CREATE_JOB") | awk '{print $NF}')
echo "Created JOB_ID: $JOB_ID"

JOB_EXECUTION=$($CONTROLLER -a "$AUTH_FILE" -r "$JOB_ID")
EXECUTION_ID=$(tail -n1 <(printf "%s" "$JOB_EXECUTION") | awk '{print $NF}')
STATE=$($CONTROLLER -a "$AUTH_FILE" -s "$EXECUTION_ID" | tail -n1 )
if ! echo "$STATE" | grep -q "completed"; then
  echo "$JOB_EXECUTION reports $STATE"
  exit 9 # Why wouldn't we use a completely arbitrary return code? It's not like 1 is considered a success.
else
  exit 0
fi
