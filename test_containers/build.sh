#!/bin/bash
#
# build.sh
#

## Minimal images for basic examples and tests.
echo "*** Build minimal test images."
docker build -t dev_test -f ./Dockerfile.dev_test .

docker image prune --force
