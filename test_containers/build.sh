#! /bin/bash
#
# build.sh
#

echo "*** Build test images."
sudo docker build -t dev_test -f ./Dockerfile.dev_test .
sudo docker build -t sec_test -f ./Dockerfile.sec_test .
sudo docker build -t nginx -f ./Dockerfile.nginx .

dangling_imgs=$(sudo docker images -f "dangling=true" -q)
echo $dangling_imgs
if [[ $dangling_imgs ]]; then
    echo "*** Remove all dangling images."
    sudo docker rmi $dangling_imgs
fi
