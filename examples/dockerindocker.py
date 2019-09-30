#!/usr/bin/python3

"""
About: Basic example of running Docker container inside Docker container Host

Topo: Chain topology  h1     h2     h3         hn
                       |      |      |          |
                      s1 --- s2 --- s3 --- ... sn
Tests:
- Ping test between internal container between head (h1) and tail (hn).
- Resource limitation test for head and tail hosts: The CPU and memory
  limitation of Dockerhost are configured to (50/n)% and 10MB. The internal
  containers try to use 100% and 300MB RAM by execute stree-ng. The actual
  resource usages are monitored and reported.
"""


import time
import argparse

from comnetsemu.net import Containernet, VNFManager
from mininet.log import info, setLogLevel
from mininet.node import Controller
from mininet.link import TCLink

# Limit the specific CPUs or cores a container can use. A comma-separated list
# or hyphen-separated range of CPUs a container can use, if you have more than
# one CPU. The first CPU is numbered 0. A valid value might be 1,3 (to use the
# second and fourth CPU).
CPU_SETS = "0"


def testDockerInDocker(n):

    net = Containernet(controller=Controller, link=TCLink)
    mgr = VNFManager(net)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding Docker hosts and switches in a chain topology\n")
    last_sw = None
    hosts = list()
    # Connect hosts
    for i in range(n):
        # Unlimited access to CPU(s) cycles in CPU_SETS
        host = net.addDockerHost(
            "h%s" % (i + 1),
            dimage="dev_test",
            ip="10.0.0.%s" % (i + 1),
            docker_args={"cpuset_cpus": "0"},
        )
        hosts.append(host)
        switch = net.addSwitch("s%s" % (i + 1))
        net.addLink(switch, host, bw=10, delay="10ms")
        if last_sw:
            # Connect switches
            net.addLink(switch, last_sw, bw=10, delay="10ms")
        last_sw = switch

    info("*** Starting network\n")
    net.start()

    info(
        "*** Run a simple ping test between two internal containers deployed on h1 and h%s\n"
        % n
    )
    head = mgr.addContainer("head", "h1", "dev_test", "/bin/bash", docker_args={})
    tail = mgr.addContainer(
        "tail", "h%s" % n, "dev_test", "ping -c 3 10.0.0.1", docker_args={}
    )

    info("*** Tail start ping head, wait for 5s...")
    time.sleep(5)
    info("\nThe ping result of tail to head: \n")
    print(tail.dins.logs().decode("utf-8"))
    mgr.removeContainer(head.name)
    mgr.removeContainer(tail.name)

    time.sleep(3)

    info("*** Run CPU resource limitation test.")
    info(
        "Update CPU limitation of all Docker hosts (h1-h%s) to %.2f %% \n"
        % (n, 50.0 / n)
    )
    info("Update Memory limitation of all Docker hosts (h1-h%s) to 10MB\n" % n)
    info(
        "Deploy the stress app (100 % CPU and 300M memory) inside all Docker hosts to test the CPU/Memory limitation\n"
    )
    containers = list()
    # Mark: CPU percent = cpu_quota / cpu_period. The default CPU period is
    # 100ms = 100000 us
    for i, h in enumerate(hosts):
        h.dins.update(cpu_quota=int(50000 / n))
        h.dins.update(mem_limit=10 * (1024 ** 2))  # in bytes
        c = mgr.addContainer(
            "stress_app_%s" % (i + 1),
            h.name,
            "dev_test",
            "stress-ng -c 1 -m 1 --vm-bytes 300M",
            docker_args={},
        )
        containers.append(c)

    info(
        "Start monitoring resource usage of internal containers"
        "with default sample count: 3 and sample period: 1 sec\n"
    )
    for c in containers:
        usages = mgr.monResourceStats(c.name)
        if usages:
            print(
                " The average CPU and Memory usage of container:{} is {:.2f}%, {:.2f}MB".format(
                    c.name,
                    (sum(u[0] for u in usages) / len(usages)),
                    (sum(u[1] for u in usages) / len(usages)),
                )
            )
        else:
            print("[ERROR] Failed to get resource usages from manager")

    for c in containers:
        mgr.removeContainer(c.name)

    info("*** Stopping network\n")
    net.stop()
    mgr.stop()


if __name__ == "__main__":
    setLogLevel("info")
    host_num = 3
    parser = argparse.ArgumentParser(
        description="Basic example for Docker-in-Docker setup."
    )
    parser.add_argument(
        "--host_num", default=3, type=int, help="Number of hosts in the chain topology"
    )
    args = parser.parse_args()
    print("*** The number of hosts in the chain: " + str(args.host_num))
    testDockerInDocker(args.host_num)
