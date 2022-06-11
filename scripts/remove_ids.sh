#!/bin/bash
# Script to delete jobs from RNAcentral-references.

set -o allexport
source $PWD/.env
set +o allexport

bad_jobs=(`psql -X -A -d $dbname -U $username -t -c "SELECT job_id FROM job WHERE job_id ~ '^[0-9]+$'"`)

for job in ${!bad_jobs[*]}
do
  # delete job
  psql -U $username -d $dbname -c "DELETE FROM job WHERE job_id='${bad_jobs[$job]}'"
done