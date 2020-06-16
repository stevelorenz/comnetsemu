#!/bin/bash

echo "Build docker image for the service migration."
docker build -t service_migration --file ./Dockerfile .
docker image prune
