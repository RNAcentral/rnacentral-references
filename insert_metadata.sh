#!/bin/bash
# Script to insert metadata in RNAcentral-references.

# set file and database
file=$1
db=$2

# -o allexport enables all following variable definitions to be exported.
# +o allexport disables this feature.
set -o allexport
source $PWD/.db_params
set +o allexport

function insertMetadata
{
  # set line and database
  line=$1
  db=$2

  # get gene, primary_id and urs
  IFS="|" read gene primary_id urs <<< "$line"

  # insert data
  psql -U $username -d $dbname -c "INSERT INTO database (job_id, name, primary_id) VALUES ((SELECT job_id FROM job WHERE LOWER(job_id)='${gene,,}'), '$db', '$urs')"
  psql -U $username -d $dbname -c "INSERT INTO database (job_id, name, primary_id) VALUES ((SELECT job_id FROM job WHERE LOWER(job_id)='${primary_id,,}'), '$db', '$urs')"
}

# loop through the file
while IFS="" read -r p || [ -n "$p" ]
do
  insertMetadata "$p" "$db"
done < "$file"