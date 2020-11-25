#!/bin/bash

docker build -t kodo_rlnc_coder -f ./Dockerfile .
docker image prune --force
