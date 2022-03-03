#!/bin/bash
set -e

# Usage: "./scripts/export/export.sh <collection name> <outfile path>"

ENV_PATH=.env
CONTAINER_NAME=mongo

if [ $# -lt 2 ]; then
    echo "Invalid aguments."
    echo "Usage: export.sh <collection name> <outfile path>"
    exit 1
fi

# load .env variables, hide from output
{
  export $(grep -v '^#' $ENV_PATH | xargs)
} &> /dev/null

COLLECTION_NAME=$1
OUTFILE_CONTAINER=/tmp/$COLLECTION_NAME.json
OUTFILE_HOST=$2

# export data
docker exec $CONTAINER_NAME mongoexport --db $MONGO_DB_NAME --collection $COLLECTION_NAME \
  --authenticationDatabase admin --username $MONGO_USER --password $MONGO_PASSWORD \
  --jsonArray --out $OUTFILE_CONTAINER

# copy file from docker container to host
docker cp $CONTAINER_NAME:$OUTFILE_CONTAINER $OUTFILE_HOST

# Remove file in container
docker exec $CONTAINER_NAME bash -c "rm $OUTFILE_CONTAINER"