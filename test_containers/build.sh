#!/bin/bash
#
# build.sh
#

## Minimal images for basic examples and tests.
echo "*** Build minimal test images."
docker build -t dev_test -f ./Dockerfile.dev_test .

## Additional images for examples.
# docker build -t network_measurement -f ./Dockerfile.network_measurement .

docker image prune --force
