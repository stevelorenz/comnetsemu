#!/bin/bash
#
# build.sh
#

echo "*** Build minimal test images."
sudo docker build -t dev_test -f ./Dockerfile.dev_test .
sudo docker build -t network_measurement -f ./Dockerfile.network_measurement .
