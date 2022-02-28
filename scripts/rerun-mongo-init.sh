#!/bin/bash
set -ex

# to make this script executeable: chmod +x run-mongo-init.sh
# The "mongo-init.js" must be present in the "/docker-entrypoint-initdb.d"-folder.

CONTAINER_NAME=mongo
ENV_PATH=.env

# load .env variables, hide from output
{
  export $(grep -v '^#' $ENV_PATH | xargs)
} &> /dev/null

docker exec $CONTAINER_NAME mongosh -u $MONGO_USER -p $MONGO_PASSWORD --authenticationDatabase admin $MONGO_DB_NAME /docker-entrypoint-initdb.d/mongo-init.js