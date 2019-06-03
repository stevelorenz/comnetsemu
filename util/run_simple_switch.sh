#! /bin/sh

RYU_VER="v4.32"
RYU_APP_DIR="$HOME/comnetsemu_dependencies/ryu-$RYU_VER/ryu/ryu/app"
RYU_APP_NAME="simple_switch.py"
OPF_PORT=10000

echo "*** Run Ryu SDN controller simple switch (OpenFlow 1.0) application"
cd "$RYU_APP_DIR" || exit
ryu-manager --ofp-ssl-listen-port $OPF_PORT --ofp-tcp-listen-port $OPF_PORT $RYU_APP_NAME
