#!/bin/bash
set -ex

# To make this script executeable: chmod +x import.sh

ENV_PATH='../../.env'
CONTAINER_NAME=mongo

# load .env variables, hide from output
{
  export $(grep -v '^#' $ENV_PATH | xargs)
} &> /dev/null

FILES="*.json"
for f in $FILES
do
  echo "Processing '$f' file..."

  COLLECTION_NAME="${f%.*}"

  # copy file to docker container
  docker cp $f $CONTAINER_NAME:/tmp/$f

  # import data
  docker exec $CONTAINER_NAME mongoimport --db $MONGO_DB_NAME --collection $COLLECTION_NAME \
    --authenticationDatabase admin --username $MONGO_USER --password $MONGO_PASSWORD \
    --drop --jsonArray --batchSize 1 --file /tmp/$f

  # Remove file in container
  docker exec $CONTAINER_NAME bash -c "rm /tmp/$f"

done