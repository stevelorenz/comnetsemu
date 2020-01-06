#!/bin/bash
#
# run.sh
#

export COMNETSEMU_AUTOTEST_MODE=1

PYTHON="python3"

echo "*** Running basic functional examples of the emulator."
$PYTHON ./dockerhost.py
$PYTHON ./dockerindocker.py

if [[ "$1" == "-a" ]]; then
    echo "*** Run additional examples."

    echo "- Run ./mininet_demystify."
    bash ./mininet_demystify/run.sh
    bash ./mininet_demystify/clean.sh

    echo "- Run ./echo_server."
    if [[ "$(docker images -q echo_server:latest 2>/dev/null)" == "" ]]; then
        cd ./echo_server/ && bash ./build_docker_images.sh
    fi
    cd ./echo_server && $PYTHON ./topology.py
fi

export COMNETSEMU_AUTOTEST_MODE=0
