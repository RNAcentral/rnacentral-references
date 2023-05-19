#!/bin/bash
# Script to get RNAcentral metadata.

# -o allexport enables all following variable definitions to be exported.
# +o allexport disables this feature.
set -o allexport
source $PWD/.db_params
set +o allexport

# get list of URS
urs_list=(`psql -X -A -d $dbname -U $username -t -c "SELECT job_id FROM job WHERE job_id like 'URS%' limit 1"`)

for urs in ${!urs_list[*]}
do
  # get related ids
  related_ids=(`psql -X -A -d $dbname -U $username -t -c "SELECT DISTINCT job_id FROM database WHERE primary_id='${urs_list[$urs]}'"`)

  # get number of articles
  counter=0
  for job in ${!related_ids[*]}
  do
    hit_count=`psql -X -A -d $dbname -U $username -t -c "SELECT hit_count FROM job WHERE job_id='${related_ids[$job]}'"`
    counter=$[$counter + $hit_count]
  done

  # add URS and number of articles to the output file
  echo "${urs_list[$urs]}|$counter" >> rnacentral_metadata.txt
done

