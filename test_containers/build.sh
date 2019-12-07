#!/bin/bash
#
# build.sh
#

echo "*** Build minimal test images."
sudo docker build -t dev_test -f ./Dockerfile.dev_test .
sudo docker build -t network_measurement -f ./Dockerfile.network_measurement .

dangling_imgs=$(sudo docker images -f "dangling=true" -q)
if [[ "$dangling_imgs" ]]; then
    echo "*** Find dangling Docker images: "
    echo "$dangling_imgs"
    echo "*** Remove all dangling images."
    sudo docker rmi "$dangling_imgs"
fi
