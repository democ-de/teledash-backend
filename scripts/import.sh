#!/bin/bash
set -e

# Usage:
# ./scripts/import/import.sh <path to JSON-files>

# Takes a directory with JSON-files and creates collections from them.
# The name of a JSON-file is the collection name.
# The content of a JSON-file is an array of document-objects.

# Warning: Using this script will drop collections before importing new documents.

ENV_PATH=.env
CONTAINER_NAME=mongo

if [ $# -eq 0 ]; then
    echo "Invalid aguments."
    echo "Usage: import.sh <path to JSON-files>"
    exit 1
fi

# load .env variables, hide from output
{
  export $(grep -v '^#' $ENV_PATH | xargs)
} &> /dev/null

FILES="$1/*.json"
for FILE_PATH_LOCAL in $FILES
do

  FILE_NAME="$(basename -- $FILE_PATH_LOCAL)"
  FILE_PATH_CONTAINER="/tmp/$FILE_NAME"
  COLLECTION_NAME="${FILE_NAME%.*}"

  echo "Processing '$FILE_NAME' file..."

  # copy file to docker container
  docker cp $FILE_PATH_LOCAL $CONTAINER_NAME:$FILE_PATH_CONTAINER

  # import data
  docker exec $CONTAINER_NAME mongoimport --db $MONGO_DB_NAME --collection $COLLECTION_NAME \
    --authenticationDatabase admin --username $MONGO_USER --password $MONGO_PASSWORD \
    --drop --jsonArray --batchSize 1 --file $FILE_PATH_CONTAINER

  # Remove file in container
  docker exec $CONTAINER_NAME bash -c "rm $FILE_PATH_CONTAINER"

done