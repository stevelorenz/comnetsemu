#!/bin/bash

echo "Build docker image for the echo server."
docker build -t echo_server --file ./Dockerfile .
