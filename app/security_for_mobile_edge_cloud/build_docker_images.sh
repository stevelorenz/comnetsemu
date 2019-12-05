#!/bin/bash

echo "Build docker images for sec_test and nginx..."
sudo docker build -t sec_test --file ./Dockerfile.sec_test .
sudo docker build -t nginx --file ./Dockerfile.nginx .
