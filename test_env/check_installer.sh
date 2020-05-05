#!/usr/bin/env bash
#
# About: Check the installer program with Docker locally
# WARN : The ComNetsEmu CAN NOT run inside Docker container, this script is
# just used to check the install, update functions of ./install.sh
#

# Fail on error
set -e

# Fail on unset var usage
set -o nounset

# TODO:  <06-06-19, Zuo> Test installation on other distributions
TEST_IMAGES=("ubuntu:18.04" "debian:buster")
TEST_OPTIONS=("-t")
COMNETSEMU_DIR="/root/comnetsemu"

for img in "${TEST_IMAGES[@]}"; do
    for opt in "${TEST_OPTIONS[@]}"; do
        echo "*** Check the installation on $img with option $opt"

        docker build -t "test_comnetsemu_install_$img" -f- . <<EOF
FROM $img

ENV COMNETSEMU_DIR=/root/comnetsemu

RUN apt-get update && apt-get install -y git make pkg-config sudo python3 libpython3-dev python3-dev python3-pip software-properties-common
WORKDIR /root
RUN mkdir -p $COMNETSEMU_DIR/comnetsemu -p $COMNETSEMU_DIR/util
COPY ./bin/ $COMNETSEMU_DIR/bin
COPY ./comnetsemu/ $COMNETSEMU_DIR/comnetsemu
COPY ./Makefile $COMNETSEMU_DIR/Makefile
COPY ./util/ $COMNETSEMU_DIR/util
COPY ./setup.py $COMNETSEMU_DIR/setup.py
COPY ./patch/ $COMNETSEMU_DIR/patch
WORKDIR $COMNETSEMU_DIR/util

RUN bash ./install.sh $opt

CMD ["bash"]
EOF
        docker image rm "test_comnetsemu_install_$img"
    done
done
