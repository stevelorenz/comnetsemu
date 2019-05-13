#! /bin/bash
#
# About: Run cleanups if the emulation did not stop properly
#

echo "# Remove all Docker containers and run Mininet cleanup"
sudo docker rm --force $(sudo docker ps -a -q)
sudo mn -c

echo "# Delete links between switches"
sw_num=10
if [[ "$1" != "" ]]; then
    sw_num=$1
fi
for (( i = 1; i < "$sw_num"; i++ )); do
    sudo ip link delete "s$i-s$((i+1))"
done
