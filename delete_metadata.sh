#!/bin/bash
# Script to delete metadata from RNAcentral-references.

# set the file based on the first argument
file=$1

# -o allexport enables all following variable definitions to be exported.
# +o allexport disables this feature.
set -o allexport
source $PWD/.db_params
set +o allexport

function deleteMetadata
{
  # get gene, primary_id and urs
  line=$1
  IFS="|" read gene primary_id urs <<< "$line"

  # delete data
  psql -U $username -d $dbname -c "DELETE FROM database WHERE LOWER(job_id)='${gene,,}' and name='rnacentral' and primary_id='$urs'"
  psql -U $username -d $dbname -c "DELETE FROM database WHERE LOWER(job_id)='${primary_id,,}' and name='rnacentral' and primary_id='$urs'"
}

# loop through the file
while IFS="" read -r p || [ -n "$p" ]
do
  deleteMetadata "$p"
done < "$file"