#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "*** Please run with sudo."
    exit 1
fi

hosts=("h1" "h2" "h3")
hsifaces=("s1-h1" "s1-h2" "s1-h3")

echo "Cleanup all network namespaces, veth pairs, qdiscs and OVS bridges."

for i in "${hsifaces[@]}"; do
    ip link delete "$i"
done

for n in "${hosts[@]}"; do
    ip netns delete "$n"
done

ovs-vsctl del-br s1

killall iperf
killall ping
