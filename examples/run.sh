#!/bin/bash
#
# run.sh
#

PYTHON="python3"

echo "*** Running basic functional examples of the emulator."
$PYTHON ./dockerhost.py
$PYTHON ./dockerindocker.py

if [[ "$1" == "-a" ]]; then
    echo "*** Run additional examples."
    $PYTHON ./wireguard.py
    $PYTHON ./nftables.py

    bash ./mininet_demystify/run.sh
    bash ./mininet_demystify/clean.sh
fi
