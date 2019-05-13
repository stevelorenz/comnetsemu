#!/usr/bin/python3

"""
Simple example of running Docker container inside Docker container Host
"""


import time

from comnetsemu.net import Containernet, VNFManager
from mininet.cli import CLI
from mininet.log import info, setLogLevel
from mininet.node import Controller, CPULimitedHost
from mininet.topo import Topo
from mininet.util import dumpNodeConnections

# Limit the specific CPUs or cores a container can use. A comma-separated list
# or hyphen-separated range of CPUs a container can use, if you have more than
# one CPU. The first CPU is numbered 0. A valid value might be 1,3 (to use the
# second and fourth CPU).
CPU_SETS = "0"


def testDockerInDocker(n=2):
    "Create a chain topology for "

    net = Containernet(controller=Controller)
    mgr = VNFManager(net)

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Adding Docker hosts and switches in a chain topology\n')
    last_sw = None
    hosts = list()
    # Connect hosts
    for i in range(n):
        # Unlimited access to CPU(s) cycles in CPU_SETS
        host = net.addDockerHost(
            'h%s' % (i + 1), dimage='dev_test', ip='10.0.0.%s' % (i + 1),
            cpuset_cpus=CPU_SETS,
            volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])
        hosts.append(host)
        switch = net.addSwitch("s%s" % (i + 1))
        net.addLink(switch, host, bw=10, delay="1ms", use_htb=True)
        if last_sw:
            # Connect switches
            net.addLink(switch, last_sw,
                        bw=10, delay="1ms", use_htb=True)
        last_sw = switch

    info('*** Starting network\n')
    net.start()

    info('*** Run a simple ping test between two internal containers deployed on h1 and h%s\n' % n)
    head = mgr.addContainer("head", "h1", "dev_test",
                            "/bin/bash")
    tail = mgr.addContainer("tail", "h%s" % n, "dev_test",
                            "ping -c 3 10.0.0.1")

    info('*** Tail start ping head, wait for 5s...')
    time.sleep(5)
    info("\nThe ping result of tail to head: \n")
    print(tail.dins.logs().decode('utf-8'))
    mgr.removeContainer(head)
    mgr.removeContainer("tail")

    time.sleep(3)

    info("*** Run CPU resource limitation test.")
    info("Update CPU limitation of all Docker hosts (h1-h%s) to %.2f %% \n" %
         (n, 50.0 / n))
    info("Update Memory limitation of all Docker hosts (h1-h%s) to 10MB\n" % n)
    info("Deploy the stress app (100 % CPU and 300M memory) inside all Docker hosts to test the CPU/Memory limitation\n")
    containers = list()
    # Mark: CPU percent = cpu_quota / cpu_period. The default CPU period is
    # 100ms = 100000 us
    for i, h in enumerate(hosts):
        h.updateCpuLimit(cpu_quota=int(50000 / n))
        h.updateMemoryLimit(mem_limit=10 * (1024**2))  # in bytes
        c = mgr.addContainer("stress_app_%s" % (i + 1), h.name,
                             "dev_test", "stress -c 1 -m 1 --vm-bytes 300M")
        containers.append(c)

    for c in containers:
        usages = mgr.monResourceStats(c)
        print(
            " The average CPU and Memory usage of container:{} is {:.2f}%, {}".format(
                c.name,
                (sum(u[0] for u in usages) / len(usages)),
                (sum(u[1] for u in usages) / len(usages))
            ))

    for c in containers:
        mgr.removeContainer(c)

    info('*** Stopping network\n')
    net.stop()
    mgr.stop()


if __name__ == '__main__':
    setLogLevel('info')
    testDockerInDocker(3)
