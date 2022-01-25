#!/bin/bash
# Script to submit ids to RNAcentral-reference
#
# Usage:   ./upload.sh [file] [database]
# Example: ./upload.sh file.txt rfam

# set file and database
file=$1
database=$2

# create folder
[ ! -d submitted ] && mkdir submitted

function submitJob
{
  # sett job_id
  job_id=$1

  if [ -z ${database} ]; then
    # submit job (only id)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${job_id}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  else
    # submit job (id and database)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${job_id}\", \"database\": \"${database}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  fi

  sleep 0.05
}

# loop through the file
while IFS="" read -r p || [ -n "$p" ]
do
  submitJob "$p"
done < "$file"