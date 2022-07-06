#!/bin/bash
# Script to submit ids to RNAcentral-reference
#
# Usage:   ./upload.sh [file] [database]
#
# The file can contain job_id, primary_id and urs_taxid.
# Each line in the file must have at least a job_id or a primary_id.
# Example:
#       5_8S_rRNA|RF00002|URS000019A91D_7230
#       Y_RNA|RF00019|
#       Ysr224||
#       ZMP-ZTP||URS0001BC94F0_256318
#       |RF01750|URS0001BC834A_408172
#       |RF02770|


# set file and database
file=$1
database=$2
primary=$3
upi=$4

# create folder
[ ! -d submitted ] && mkdir submitted

function submitJob
{
  line=$1
  IFS=$'|'
  tmp=($line)

  if [ -z ${primary} ] && [ -z ${upi} ]; then
    # set job_id, primary_id and urs
    job_id="${tmp[0]}"
    primary_id="${tmp[1]}"
    urs="${tmp[2]}"
  elif [ -z ${primary} ]; then
    # set job_id and primary_id
    job_id="${tmp[0]}"
    primary_id="${tmp[1]}"
  else
    # set job_id
    job_id="${tmp[1]}"
  fi

  # submit search according to the parameters used
  if [ -z ${primary_id} ] && [ -z ${urs} ]; then
    # submit job (id and database)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${job_id}\", \"database\": \"${database}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  elif [ -z ${job_id} ] && [ -z ${urs} ]; then
    # submit job (primary_id and database)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${primary_id}\", \"database\": \"${database}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  elif [ -z ${urs} ]; then
    # submit job (id, primary_id and database)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${job_id}\", \"primary_id\": \"${primary_id}\", \"database\": \"${database}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  elif [ -z ${primary_id} ]; then
    # submit job (id, urs and database)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${job_id}\", \"database\": \"${database}\", \"urs\": \"${urs}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  elif [ -z ${job_id} ]; then
    # submit job (primary_id, urs and database)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${primary_id}\", \"database\": \"${database}\", \"urs\": \"${urs}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  else
    # submit job (id, database, primary_id, urs)
    curl -X POST \
         -H "Content-Type:application/json" \
         -d "{\"id\": \"${job_id}\", \"database\": \"${database}\", \"primary_id\": \"${primary_id}\", \"urs\": \"${urs}\"}" \
         http://45.88.80.122:8080/api/submit-job && echo ${job_id} >> submitted/${file};
  fi

  sleep 0.05
}

# loop through the file
while IFS="" read -r p || [ -n "$p" ]
do
  submitJob "$p"
done < "$file"