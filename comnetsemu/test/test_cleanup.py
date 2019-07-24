"""
About: Test the cleanup function of ce CLI utility
"""

from subprocess import run

from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

CPU_SETS = "0"


def testDockerInDocker(n=2, err=False):

    net = Containernet(controller=Controller, link=TCLink)
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
    mgr.addContainer("head", "h1", "dev_test",
                     "/bin/bash")
    mgr.addContainer("tail", "h%s" % n, "dev_test",
                     "ping -c 3 10.0.0.1")

    info("*** Run CPU resource limitation test.")
    info("Update CPU limitation of all Docker hosts (h1-h%s) to %.2f %% \n" %
         (n, 50.0 / n))
    info("Update Memory limitation of all Docker hosts (h1-h%s) to 10MB\n" % n)
    info("Deploy the stress app (100 % CPU and 300M memory) inside all Docker hosts to test the CPU/Memory limitation\n")
    containers = list()

    for i, h in enumerate(hosts):
        h.updateCpuLimit(cpu_quota=int(50000 / n))
        h.updateMemoryLimit(mem_limit=10 * (1024**2))  # in bytes
        c = mgr.addContainer("stress_app_%s" % (i + 1), h.name,
                             "dev_test", "stress -c 1 -m 1 --vm-bytes 300M")
        containers.append(c)

    if err:
        info("Something wrong happens, unfortunately, the emulation failed to stop...\n")
        1 / 0

    for c in containers:
        mgr.removeContainer(c)

    info('*** Stopping network\n')
    net.stop()
    mgr.stop()


if __name__ == '__main__':
    setLogLevel('info')

    try:
        testDockerInDocker(3, err=True)
    except Exception:
        ret = run(["sudo", "ce", "-c"])
        print(ret)
    testDockerInDocker(3)
