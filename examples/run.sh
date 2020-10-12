#!/bin/bash
#
# run.sh
#

if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo."
    exit
fi

set -o errexit
set -o nounset
set -o pipefail

export COMNETSEMU_AUTOTEST_MODE=1

PYTHON="python3"

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "-a     Run additional examples."
}

run_examples() {
    echo "*** Running basic functional examples of the emulator."
    $PYTHON ./dockerhost.py
    $PYTHON ./dockerindocker.py
    echo "- Run ./dockerhost_manage_appcontainer.py"
    $PYTHON ./dockerhost_manage_appcontainer.py

    pushd "$PWD"
    cd ./echo_server/
    echo "- Run ./echo_server."
    if [[ "$(docker images -q echo_server:latest 2>/dev/null)" == "" ]]; then
        bash ./build_docker_images.sh
    fi
    $PYTHON ./topology.py
    popd
}

run_additional_examples() {
    echo "*** Run additional examples."

    echo "- Run ./mininet_demystify."
    bash ./mininet_demystify/run.sh
    bash ./mininet_demystify/clean.sh
}

if [[ "$#" -eq 0 ]]; then
    run_examples
elif [[ $1 == "-a" ]]; then
    run_examples
    run_additional_examples
else
    echo "ERROR: Unknown option."
    usage
fi

export COMNETSEMU_AUTOTEST_MODE=0
