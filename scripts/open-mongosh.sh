#!/bin/bash
set -ex

CONTAINER_NAME=mongo
ENV_PATH=.env

# load .env variables, hide from output
{
  export $(grep -v '^#' $ENV_PATH | xargs)
} &> /dev/null

docker exec -it $CONTAINER_NAME mongosh -u $MONGO_USER -p $MONGO_PASSWORD --authenticationDatabase admin $MONGO_DB_NAME