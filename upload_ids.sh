#!/bin/bash
# Script to submit ids to RNAcentral-reference
#
# Usage:   ./upload.sh [file] [database] [primary_id]
#
# Using as an example a file containing the following lines:
#       hsa-miR-410-3p|MIMAT0002171
#       sbi-MIR168|MI0001556
#
# To search with the primary id (MIMAT0002171 and MI0001556), run the command:
# Example: ./upload.sh file.txt mirbase true
#
# To search with other ids (hsa-miR-410-3p and sbi-MIR168), but registering the primary id, run the command:
# Example: ./upload.sh file.txt mirbase

# set file and database
file=$1
database=$2
primary=$3

# create folder
[ ! -d submitted ] && mkdir submitted

function submitJob
{
  line=$1
  IFS=$'|'
  tmp=($line)

  # set job_id and primary_id (optional)
  if [ -z ${primary} ]; then
    # search id and register primary_id
    job_id="${tmp[0]}"
    primary_id="${tmp[1]}"
  else
    # do the search using the primary_id
    job_id="${tmp[1]}"
  fi

  # submit search according to the parameters used
  if [ -z ${database} ] && [ -z ${primary_id} ]; then
    # submit job (only id)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${job_id}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  elif [ -z ${primary_id} ]; then
    # submit job (id and database)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${job_id}\", \"database\": \"${database}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  elif [ -z ${database} ]; then
    # submit job (id and primary_id)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${job_id}\", \"primary_id\": \"${primary_id}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  else
    # submit job (id, database and primary_id)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${job_id}\", \"database\": \"${database}\", \"primary_id\": \"${primary_id}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  fi

  sleep 0.05
}

# loop through the file
while IFS="" read -r p || [ -n "$p" ]
do
  submitJob "$p"
done < "$file"