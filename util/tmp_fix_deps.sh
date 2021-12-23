#!/bin/bash
#
# tmp_fix_deps.sh
#
# This script contains some temporary fixes for upstream dependencies
#

echo "* Pin eventlet version (0.30.2) for Ryu SDN controller"
echo "Check: https://github.com/faucetsdn/ryu/issues/138"
sudo pip3 install eventlet==0.30.2
