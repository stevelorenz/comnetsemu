#! /bin/bash

echo "Build docker image for NC coders (encoder, recoder and decoder)..."
docker build -t nc_coder --file ./Dockerfile .
