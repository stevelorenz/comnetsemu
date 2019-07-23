"""
About: ComNetsEmu Network
"""

import sys
from time import sleep
import os

import docker
from comnetsemu.node import DockerContainer, DockerHost
from comnetsemu.cli import spawnAttachedXterm
from mininet.link import TCIntf
from mininet.log import debug, error, info, output, warn
from mininet.net import Mininet
from mininet.node import Switch
from mininet.util import BaseString
from mininet.term import makeTerms, cleanUpScreens

# ComNetsEmu version: should be consistent with README and LICENSE
VERSION = "0.1.3"


class Containernet(Mininet):
    """A Mininet sub-class with DockerHost related methods."""

    def __init__(self, **params):
        Mininet.__init__(self, **params)

    def addDockerHost(self, name, cls=DockerHost, **params):
        """
        Wrapper for addHost method that adds a
        Docker container as a host.
        """
        return self.addHost(name, cls=cls, **params)

    def addLink(self, node1, node2, port1=None, port2=None,
                cls=None, **params):
        # MARK: Node1 should be the switch for DockerHost
        if isinstance(node1, DockerHost) and isinstance(node2, Switch):
            error("Switch should be the node1 to connect a DockerHost\n")
            self.stop()
            sys.exit(1)
        else:
            super(Containernet, self).addLink(node1, node2, port1, port2, cls,
                                              **params)

    def startTerms(self):
        "Start a terminal for each node."
        if 'DISPLAY' not in os.environ:
            error("Error starting terms: Cannot connect to display\n")
            return
        info("*** Running terms on %s\n" % os.environ['DISPLAY'])
        cleanUpScreens()
        self.terms += makeTerms(self.controllers, 'controller')
        self.terms += makeTerms(self.switches, 'switch')
        dhosts = [h for h in self.hosts if isinstance(h, DockerHost)]
        for d in dhosts:
            self.terms.append(spawnAttachedXterm(d.name))
        rest = [h for h in self.hosts if h not in dhosts]
        self.terms += makeTerms(rest, 'host')

    def addLinkNamedIfce(self, src, dst, *args, **kwargs):
        """Add a link with named two interfaces
           - Name of interface 1: src-dst
           - Name of interface 2: dst-src
        """
        # Accept node objects or names
        src = src if not isinstance(src, BaseString) else self[src]
        dst = dst if not isinstance(dst, BaseString) else self[dst]
        self.addLink(src, dst,
                     intfName1="-".join((src.name, dst.name)),
                     intfName2="-".join((dst.name, src.name)),
                     *args, **kwargs)

    def change_host_ifce_loss(self, host, ifce, loss, parent=" parent 5:1"):
        if isinstance(host, BaseString):
            host = self.net.get(host)
        if not host:
            error("Can not find the running host\n")
            return False
        tc_ifce = host.intf(ifce)
        if not isinstance(tc_ifce, TCIntf):
            error("The interface must be a instance of TCIntf\n")
            return False

        # WARN: The parent number is defined in mininet/link.py
        ret = host.cmd(
            "tc qdisc change dev {} {} handle 10: netem loss {}%".format(
                ifce, parent, loss
            ))
        if ret != "":
            error("Failed to change loss. Error:%s\n", ret)
            return False

        return True

    def stop(self):
        super(Containernet, self).stop()


class VNFManager(object):

    """Manager for VNFs deployed on Mininet hosts (Docker in Docker)

    - To make is simple. It uses docker-py APIs to manage internal containers
      from host system.

    - It should communicate with SDN controller to manage internal containers
      adaptively.

    """

    def __init__(self, net):
        """Init the VNFManager

        :param net (Mininet): The mininet object, used to manage hosts via
        Mininet's API
        """
        self.net = net
        self.dclt = docker.from_env()

        self.container_queue = list()
        self.name_container_map = dict()

        # mininet's internal containers -> mni
        self.dnameprefix = "mni"

    def addContainer(self, name, dhost, dimage, dcmd, retry_cnt=3, wait=0.5,
                     **params):
        """Create and run a new container inside a Mininet DockerHost

        The manager retries with retry_cnt times to create the container if the
        dhost can not be found via docker-py API, but can be found in the
        Mininet host list. This happens during e.g. updating the CPU limitation
        of a running DockerHost instance.

        :param name (str): Name of the container
        :param dhost (str or Node): The name or instance of the to be deployed DockerHost instance
        :param dimage (str): The name of the docker image
        :param dcmd (str): Command to run after the creation
        :param retry_cnt (int): Number of retries if failed to get the DockerHost
        """
        if isinstance(dhost, BaseString):
            dhost = self.net.get(dhost)
        if not dhost:
            error(
                "The internal container must be deployed on a running DockerHost instance \n")
            return None

        # Create container INSIDE Containernet host

        # 1. Here exec the 'docker run' directly in DockerHost instance instead
        # of using docker-py APIs is a workaround: The docker-py does not
        # provide how to use --cgroup-parent API directly. Should be replace
        # with docker-py APIs if cgroup-parent feature is supported.

        # 2. Current version, the container inside share the network stack of
        # the parent docker.
        name = ".".join((self.dnameprefix, name))
        run_cmd = """docker run -idt --name {} --cgroup-parent=/docker/{} \
--network container:mn.{} {} {}
        """.format(name, dhost.did, dhost.name, dimage, dcmd)
        out = dhost.cmd(run_cmd)
        debug("\n" + out + "\n")

        cnt = 0
        while cnt < retry_cnt:
            try:
                dins = self.dclt.containers.get(name)
            except docker.errors.NotFound:
                error("Failed to get container:%s, try %d/%d times\n" % (
                    name, cnt+1, retry_cnt))
                cnt += 1
                sleep(wait)
            else:
                break

        container = DockerContainer(name, dhost, dimage, dins)

        self.container_queue.append(container)
        self.name_container_map[container.name] = container
        return container

    def removeContainer(self, container):
        """Remove the internal container

        its name)
        :param container (str or DockerContainer): Internal container object (or

        :return: Return True/False for success/fail remove.
        """

        if not container:
            return False

        if isinstance(container, BaseString):
            container = self.name_container_map.get(container, None)

        try:
            self.container_queue.remove(container)
        except ValueError:
            error("Container not found, Cannot remove it.\n")
            return False
        else:
            container.dins.remove(force=True)
            del self.name_container_map[container.name]
            return True

    @staticmethod
    def calculate_cpu_percent(stats):
        """Calculate the CPU usage in percent with given stats JSON data.

        :param stats (json):
        """
        cpu_count = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
        cpu_percent = 0.0
        cpu_delta = float(stats["cpu_stats"]["cpu_usage"]["total_usage"]) - \
            float(stats["precpu_stats"]["cpu_usage"]["total_usage"])
        system_delta = float(stats["cpu_stats"]["system_cpu_usage"]) - \
            float(stats["precpu_stats"]["system_cpu_usage"])
        if system_delta > 0.0:
            cpu_percent = cpu_delta / system_delta * 100.0 * cpu_count

        if cpu_percent > 100:
            cpu_percent = 100

        return cpu_percent

    def monResourceStats(self, container, sample_num=3, sample_period=1):
        """Monitor the resource stats of a container within a given time

        :param container (str or DockerContainer): Internal container object (or
        its name)
        :param mon_time (float): Monitoring time in seconds
        """

        if isinstance(container, BaseString):
            container = self.name_container_map.get(container, None)

        if not container:
            return list()

        n = 0
        usages = list()
        while n < sample_num:
            stats = container.dins.stats(decode=False, stream=False)
            mem_stats = stats["memory_stats"]
            mem_usg = mem_stats["usage"] / (1024 ** 2)
            cpu_usg = self.calculate_cpu_percent(stats)
            usages.append((cpu_usg, mem_usg))
            sleep(sample_period)
            n += 1

        return usages

    #  TODO:  <collmann> Add migration methods with:
    #  1. Docker built-in migration
    #  2. Distributed storage based state-sync

    def stop(self):
        debug("STOP: {} containers in the VNF queue: {}\n".format(
            len(self.container_queue),
            ", ".join((c.name for c in self.container_queue))
        ))

        # Avoid missing delete internal containers manually before stop
        for c in self.container_queue:
            c.terminate()
            c.dins.remove(force=True)

        self.dclt.close()
