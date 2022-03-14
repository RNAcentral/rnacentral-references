#!/bin/bash
# Script to insert metadata in RNAcentral-references.

# set the file based on the first argument
file=$1

# -o allexport enables all following variable definitions to be exported.
# +o allexport disables this feature.
set -o allexport
source $PWD/.db_params
set +o allexport

function insertMetadata
{
  # get gene, primary_id and urs
  line=$1
  IFS="|" read gene primary_id urs <<< "$line"

  # insert data
  psql -U $username -d $dbname -c "INSERT INTO database (job_id, name, primary_id) VALUES ('$gene', 'rnacentral', '$urs')"
  psql -U $username -d $dbname -c "INSERT INTO database (job_id, name, primary_id) VALUES ('$primary_id', 'rnacentral', '$urs')"
}

# loop through the file
while IFS="" read -r p || [ -n "$p" ]
do
  insertMetadata "$p"
done < "$file"