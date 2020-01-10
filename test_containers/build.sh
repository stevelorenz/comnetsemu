#!/bin/bash
#
# build.sh
#

echo "*** Build minimal test images."
docker build -t dev_test -f ./Dockerfile.dev_test .
docker build -t network_measurement -f ./Dockerfile.network_measurement .
docker image prune --force
