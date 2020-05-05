#!/bin/bash

docker build --rm -t dpdk:19.08 -f ./Dockerfile . && docker image prune -f
