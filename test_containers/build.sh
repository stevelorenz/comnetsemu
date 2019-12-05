#!/bin/bash
#
# build.sh
#

echo "*** Build minimal test images."
sudo docker build -t dev_test -f ./Dockerfile.dev_test .

dangling_imgs=$(sudo docker images -f "dangling=true" -q)
if [[ "$dangling_imgs" ]]; then
    echo "*** Find dangling Docker images: "
    echo "$dangling_imgs"
    echo "*** Remove all dangling images."
    sudo docker rmi "$dangling_imgs"
fi
