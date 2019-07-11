#! /bin/bash
#
# build.sh
#

sudo docker build -t dev_test -f ./Dockerfile.dev_test .
sudo docker build -t alpine_dockerhost -f ./Dockerfile.alpine_dockerhost .
sudo docker build -t sec_test -f ./Dockerfile.sec_test .
sudo docker build -t nginx -f ./Dockerfile.nginx .
