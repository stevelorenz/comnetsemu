#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "*** Please run with sudo."
    exit 1
fi

echo "* Create network namespaces for hosts."
ip netns add h1
ip netns add h2
ip netns add h3

echo "* Create veth pairs."
ip link add h1-s1 type veth peer name s1-h1
ip link add h2-s1 type veth peer name s1-h2
ip link add h3-s1 type veth peer name s1-h3

echo "* Configure veth pairs. Set the namespace of the host's interface."
echo "* Assign IP to host's interface and set the status of all links to up."
ip link set h1-s1 netns h1
ip netns exec h1 ip addr add 10.0.0.1/24 dev h1-s1
ip netns exec h1 ip link set h1-s1 up
ip link set h2-s1 netns h2
ip netns exec h2 ip addr add 10.0.0.2/24 dev h2-s1
ip netns exec h2 ip link set h2-s1 up
ip link set h3-s1 netns h3
ip netns exec h3 ip addr add 10.0.0.3/24 dev h3-s1
ip netns exec h3 ip link set h3-s1 up
ip link set s1-h1 up
ip link set s1-h2 up
ip link set s1-h3 up
echo "* Interfaces in the root namespace."
ip addr
echo "* Interfaces in the h1 namespace."
ip netns exec h1 ip addr
echo "* Interfaces in the h2 namespace."
ip netns exec h2 ip addr
echo "* Interfaces in the h3 namespace."
ip netns exec h3 ip addr

echo "* Create OVS bridge s1."
ovs-vsctl add-br s1
echo "* Add veth interfaces in the root namespace to the OVS."
ovs-vsctl add-port s1 s1-h1
ovs-vsctl add-port s1 s1-h2
ovs-vsctl add-port s1 s1-h3
echo "* The port status of the bridge s1"
ovs-vsctl show

echo "* Limit the bandwidth to 10Mbit with HTB."
echo "* Add 100ms delay and 10% losses between h1 and s1 (bidirectional)."
# The name of the root is 1:, used as the parent parameter for classes.
tc qdisc add dev s1-h1 root handle 1: htb default 1
tc class add dev s1-h1 parent 1: classid 1:1 htb rate 10mbit burst 15k
tc qdisc add dev s1-h1 parent 1:1 handle 10: netem delay 100ms loss 10
ip netns exec h1 tc qdisc add dev h1-s1 root handle 1: htb default 1
ip netns exec h1 tc class add dev h1-s1 parent 1: classid 1:1 htb rate 10mbit burst 15k
ip netns exec h1 tc qdisc add dev h1-s1 parent 1:1 handle 10: netem delay 100ms loss 10

echo "# Run tests between hosts"
# Warm up
ip netns exec h1 ping -q -c 3 10.0.0.2 >/dev/null
echo "* h1 ping h2 (quite mode, summary is printed)"
ip netns exec h1 ping -q -c 10 -i 0.5 10.0.0.2
echo "* Run iperf test between h1 and h2"
ip netns exec h2 iperf -s -u >/dev/null 2>&1 &
ip netns exec h1 iperf -c 10.0.0.2 -u -t 10 -b 100M

echo "* Add a OpenFlow entry to forward all ICMP packets from h1 with destination IP 10.0.0.2 to h3 (10.0.0.3)"
ovs-ofctl add-flow s1 "icmp,in_port=1,actions=output=3"
ip netns exec h1 ping -q -c 17 -i 1 10.0.0.2 >/dev/null 2>&1 &
echo "* Run tcpdump on host h3 to capture 3 packets"
echo "Dump all flow entries in s1's tables"
ip netns exec h3 tcpdump -i h3-s1 -c 3 -e -vv
ovs-ofctl dump-flows s1
killall iperf ping > /dev/null 2>&1

echo "* Create a cgroup named testgroup0 for CPU resource."
echo "- Run only on core 0"
echo "- The maximal usage is limited to 10%"
mkdir /sys/fs/cgroup/cpu,cpuacct/testgroup0
mkdir /sys/fs/cgroup/cpuset/testgroup0
echo 0 >/sys/fs/cgroup/cpuset/testgroup0/cpuset.cpus
# The default cfs_period_us = 100,000 us
# For CFS scheduler, CPU percentage ~= (cfs_quota_us/cfs_period_us)
echo 10000 >/sys/fs/cgroup/cpu/testgroup0/cpu.cfs_quota_us
echo "* Run a process aiming to eating 100% CPU in testgroup0 and in network namespace h1."
cgexec -g cpu,cpuacct:testgroup0 ip netns exec h1 dd if=/dev/zero of=/dev/null &
sleep 3
echo "* Check the CPU usage of this process. Format: (PID, CPU usage (%), command)"
ps ax -o pid,%cpu,comm | grep -w "dd"
killall dd

echo "* Tests finished."
