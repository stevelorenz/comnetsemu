#!/bin/bash
#
# run.sh
#

export COMNETSEMU_AUTOTEST_MODE=1

PYTHON="python3"

echo "*** Running basic functional examples of the emulator."
$PYTHON ./dockerhost.py
$PYTHON ./dockerindocker.py
echo "- Run ./dockerhost_manage_appcontainer.py"
$PYTHON ./dockerhost_manage_appcontainer.py

pushd $PWD
cd ./echo_server/
echo "- Run ./echo_server."
if [[ "$(docker images -q echo_server:latest 2>/dev/null)" == "" ]]; then
    bash ./build_docker_images.sh
fi
$PYTHON ./topology.py
popd

if [[ "$1" == "-a" ]]; then
    echo "*** Run additional examples."

    echo "- Run ./mininet_demystify."
    bash ./mininet_demystify/run.sh
    bash ./mininet_demystify/clean.sh

    echo "- Run ./network_measurement.py"
    $PYTHON ./network_measurement.py

fi

export COMNETSEMU_AUTOTEST_MODE=0
