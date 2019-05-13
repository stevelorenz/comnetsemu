"""
About: ComNetsEmu Network
"""

import ipaddress
import shlex
import sys
from subprocess import Popen
from time import sleep

import docker
from comnetsemu.node import DockerContainer, DockerHost
from mininet.log import debug, error, info, output, warn
from mininet.net import Mininet
from mininet.node import OVSBridge, Switch
from mininet.util import BaseString

# ComNetsEmu version: should be consistent with README and LICENSE
VERSION = "0.1.0"


# If an external SAP (Service Access Point) is made, it is deployed with this prefix in the name,
# so it can be removed at a later time
SAP_PREFIX = 'sap.'


class Containernet(Mininet):
    """
    A Mininet with DockerHost related methods.
    Inherits Mininet.
    This class is not more than API beautification.
    """

    def __init__(self, **params):
        # call original Mininet.__init__
        Mininet.__init__(self, **params)
        self.SAPswitches = dict()

    def addDockerHost(self, name, cls=DockerHost, **params):
        """
        Wrapper for addHost method that adds a
        Docker container as a host.
        """
        return self.addHost(name, cls=cls, **params)

    # def removeDockerHost( self, name, **params):
    #    """
    #    Wrapper for removeHost. Just to be complete.
    #    """
    #    return self.removeHost(name, **params)

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

    def addExtSAP(self, sapName, sapIP, dpid=None, **params):
        """
        Add an external Service Access Point, implemented as an OVSBridge
        :param sapName:
        :param sapIP: str format: x.x.x.x/x
        :param dpid:
        :param params:
        :return:
        """
        SAPswitch = self.addSwitch(sapName, cls=OVSBridge, prefix=SAP_PREFIX,
                                   dpid=dpid, ip=sapIP, **params)
        self.SAPswitches[sapName] = SAPswitch

        NAT = params.get('NAT', False)
        if NAT:
            self.addSAPNAT(SAPswitch)

        return SAPswitch

    def removeExtSAP(self, sapName):
        SAPswitch = self.SAPswitches[sapName]
        info('stopping external SAP:' + SAPswitch.name + ' \n')
        SAPswitch.stop()
        SAPswitch.terminate()

        self.removeSAPNAT(SAPswitch)

    def addSAPNAT(self, SAPSwitch):
        """
        Add NAT to the Containernet, so external SAPs can reach the outside internet through the host
        :param SAPSwitch: Instance of the external SAP switch
        :param SAPNet: Subnet of the external SAP as str (eg. '10.10.1.0/30')
        :return:
        """
        SAPip = SAPSwitch.ip
        SAPNet = str(ipaddress.IPv4Network(SAPip, strict=False))
        # due to a bug with python-iptables, removing and finding rules does not succeed when the mininet CLI is running
        # so we use the iptables tool
        # create NAT rule
        rule0_ = "iptables -t nat -A POSTROUTING ! -o {0} -s {1} -j MASQUERADE".format(
            SAPSwitch.deployed_name, SAPNet)
        p = Popen(shlex.split(rule0_))
        p.communicate()

        # create FORWARD rule
        rule1_ = "iptables -A FORWARD -o {0} -j ACCEPT".format(
            SAPSwitch.deployed_name)
        p = Popen(shlex.split(rule1_))
        p.communicate()

        rule2_ = "iptables -A FORWARD -i {0} -j ACCEPT".format(
            SAPSwitch.deployed_name)
        p = Popen(shlex.split(rule2_))
        p.communicate()

        info(
            "added SAP NAT rules for: {0} - {1}\n".format(SAPSwitch.name, SAPNet))

    def removeSAPNAT(self, SAPSwitch):

        SAPip = SAPSwitch.ip
        SAPNet = str(ipaddress.IPv4Network(SAPip, strict=False))
        # due to a bug with python-iptables, removing and finding rules does not succeed when the mininet CLI is running
        # so we use the iptables tool
        rule0_ = "iptables -t nat -D POSTROUTING ! -o {0} -s {1} -j MASQUERADE".format(
            SAPSwitch.deployed_name, SAPNet)
        p = Popen(shlex.split(rule0_))
        p.communicate()

        rule1_ = "iptables -D FORWARD -o {0} -j ACCEPT".format(
            SAPSwitch.deployed_name)
        p = Popen(shlex.split(rule1_))
        p.communicate()

        rule2_ = "iptables -D FORWARD -i {0} -j ACCEPT".format(
            SAPSwitch.deployed_name)
        p = Popen(shlex.split(rule2_))
        p.communicate()

        info(
            "remove SAP NAT rules for: {0} - {1}\n".format(SAPSwitch.name, SAPNet))

    def stop(self):
        super(Containernet, self).stop()

        info('*** Removing NAT rules of %i SAPs\n' % len(self.SAPswitches))
        for SAPswitch in self.SAPswitches:
            self.removeSAPNAT(self.SAPswitches[SAPswitch])
        info("\n")


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
                debug("Failed to get container %s\n" % name)
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

        :param container (str or DockerContainer): Internal container object (or
        its name)

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
