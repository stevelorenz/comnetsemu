#!/bin/bash

echo "Build docker images for sec_test and nginx..."
docker build -t sec_test --file ./Dockerfile.sec_test .
docker build -t nginx --file ./Dockerfile.nginx .
