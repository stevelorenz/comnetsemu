"""
About: ComNetsEmu Node
"""

import os
import pty
import select
import shlex
import tempfile
import time

from sys import exit
from time import sleep

import docker

from comnetsemu.exceptions import InvalidDockerArgs
from comnetsemu.log import debug, error, info, warn, output
from comnetsemu.util import checkListeningOnPort, dpidToStr

from mininet.moduledeps import pathCheck
from mininet.node import Host, Switch


class DockerHost(Host):
    """Node that represents a docker container.

    This part is inspired by:
    - http://techandtrains.com/2014/08/21/docker-container-as-mininet-host/
    - DockerHost implementation from Patrick Ziegler (patrick.ziegler@tu-dresden.de)
    """

    docker_args_default = {
        "init": True,
        "tty": True,  # -t
        "detach": True,  # -d
        # Used for cleanups
        "auto_remove": True,
        "labels": {"comnetsemu": "dockerhost"},
        "network_mode": "bridge",
        "stdin_open": True,
        # Required to setup veth inside the container by Mininet
        "privileged": True,
    }

    def __init__(
        self,
        name: str,
        dimage: str,
        docker_args: dict = None,
        dcmd: str = None,
        ishell: str = "bash",
        ishell_args: str = "--norc -is",
        **kwargs,
    ):
        """
        Creates a Docker container as Mininet host.

        :param name: Name of the DockerHost.
        :param dimage: Name of the docker image.
        :param docker_args (dict): All other keyword arguments supported by Docker-py.
            e.g. CPU and memory related limitations. Some parameters are overriden for DockerHost's functionalities.
        :param dcmd: Command to execute when create the DockerHost.
        :param ishell: The command to run interactive shell on the host.
        :param ishell_args: Arguments for running the ishell.

        :var dins: Docker container instance created by the Docker-py run API.
            Check https://docker-py.readthedocs.io/en/stable/containers.html#container-objects
            for details.
        """
        self.name = name
        self.dcmd = dcmd if dcmd is not None else "/usr/bin/env sh"
        self.dimage = dimage
        self.ishell = ishell
        self.ishell_args = ishell_args
        self.docker_args = docker_args if docker_args is not None else dict()

        self.dclient = docker.from_env()
        self.dcli = self.dclient.api
        # Container object instance created via self.dclient API
        self.dins = None
        self.master = None
        self.slave = None
        self.resources = dict()

        # Override the essential parameters
        for key in self.docker_args_default:
            if key in docker_args:
                error(
                    f"Given argument: {key} is invalid. This key is reserved for internal usages."
                )
                raise InvalidDockerArgs

        self.docker_args.update(self.docker_args_default)
        self.docker_args["name"] = self.name
        self.docker_args["command"] = self.dcmd
        self.docker_args["image"] = self.dimage

        # FIXME(Zuo): Remove this in v1.0
        # Legacy arguments given in kwargs
        legacy_opts = {
            "cpu_quota": -1,
            "cpu_period": 100000,
            "cpu_shares": None,
            "cpuset_cpus": None,
            "mem_limit": None,
            "memswap_limit": None,
            "volumes": [],
            "network_mode": None,
            "publish_all_ports": True,
            "port_bindings": {},
            "ports": [],
            "dns": [],
        }
        # Check legacy options in **kwargs, for backward capacity
        for arg in legacy_opts:
            if arg in kwargs.keys():
                error(f"Argument {arg} should be given in docker_args dictionary!\n")

        debug("Created docker container object %s\n" % name)
        debug("image: %s\n" % str(self.dimage))
        debug("Before creating the container\n")
        # Create and run the new docker container
        self.dins = self.dclient.containers.run(**self.docker_args)
        while not self.dins.attrs["State"]["Running"]:
            time.sleep(0.01)
            self.dins.reload()  # refresh information in 'attrs'

        debug("Docker container %s started. ID:%s\n" % (name, self.dins.id))
        super(DockerHost, self).__init__(name, **kwargs)

    # Command support via shell process in namespace
    def startShell(self):
        "Start a shell process for running commands"
        if self.shell:
            error("%s: shell is already running\n" % self.name)
            return

        # bash -i: force interactive
        # -s: pass $* to shell, and make process easy to find in ps
        # prompt is set to sentinel chr( 127 )
        cmd = [
            "docker",
            "exec",
            "-it",
            self.name,
            "env",
            "PS1=" + chr(127),
            "mininet:" + self.name,
        ]
        debug("Insert interactive shell bin and args")
        cmd.insert(-1, self.ishell)
        ishell_args = shlex.split(self.ishell_args)
        for a in ishell_args:
            cmd.insert(-1, a)

        # Spawn a shell subprocess in a pseudo-tty, to disable buffering
        # in the subprocess and insulate it from signals (e.g. SIGINT)
        # received by the parent
        self.master, self.slave = pty.openpty()
        debug("Docker host master:{}, slave:{}\n".format(self.master, self.slave))
        self.shell = self._popen(
            cmd, stdin=self.slave, stdout=self.slave, stderr=self.slave, close_fds=False
        )
        self.stdin = os.fdopen(self.master, "r")
        self.stdout = self.stdin
        self.pid = self.dins.attrs["State"]["Pid"]
        self.pollOut = select.poll()
        self.pollOut.register(self.stdout)
        # Maintain mapping between file descriptors and nodes
        # This is useful for monitoring multiple nodes
        # using select.poll()
        self.outToNode[self.stdout.fileno()] = self
        self.inToNode[self.stdin.fileno()] = self
        self.execed = False
        self.lastCmd = None
        self.lastPid = None
        self.readbuf = ""
        # Wait for prompt
        while True:
            data = self.read(1024)
            if data[-1] == chr(127):
                break
            self.pollOut.poll()
        self.waiting = False
        # +m: disable job control notification
        self.cmd("unset HISTFILE; stty -echo; set +m")
        debug("After Docker host master:{}, slave:{}\n".format(self.master, self.slave))

    def cleanup(self):
        if self.shell:
            # Close ptys
            self.stdin.close()
            if self.slave:
                os.close(self.slave)
            if self.waitExited:
                debug("waiting for", self.pid, "to terminate\n")
                self.shell.wait()
        self.shell = None
        self.dclient.close()

    def terminate(self):
        """Stop docker container"""
        if not self._is_container_running():
            return
        try:
            debug("Try to remove container. ID:{}\n".format(self.dins.id))
            self.dins.remove(force=True)
        except docker.errors.APIError as e:
            print(e)
            warn("Warning: API error during container removal.\n")

        debug(
            "Terminate. Docker host master:{}, slave:{}\n".format(
                self.master, self.slave
            )
        )
        self.cleanup()

    def sendCmd(self, *args, **kwargs):
        """Send a command, followed by a command to echo a sentinel,
        and return without waiting for the command to complete."""
        self._check_shell()
        if not self.shell:
            return
        Host.sendCmd(self, *args, **kwargs)

    def popen(self, *args, **kwargs):
        """Return a Popen() object in node's namespace
        args: Popen() args, single list, or string
        kwargs: Popen() keyword args"""
        if not self._is_container_running():
            error(
                "ERROR: Can't connect to Container '%s'' for docker host '%s'!\n"
                % (self.dins.id, self.name)
            )
            return None
        # MARK: Use -t option to allocate pseudo-TTY for each DockerHost
        mncmd = ["docker", "exec", "-t", f"{self.name}"]
        return Host.popen(self, *args, mncmd=mncmd, **kwargs)

    def cmd(self, *args, **kwargs):
        """Send a command, wait for output, and return it.
        cmd: string"""
        verbose = kwargs.get("verbose", False)
        log = info if verbose else debug
        log("*** %s : %s\n" % (self.name, args))
        self.sendCmd(*args, **kwargs)
        return self.waitOutput(verbose)

    def _check_shell(self):
        """Verify if shell is alive and
        try to restart if needed"""
        if self._is_container_running():
            if self.shell:
                self.shell.poll()
                if self.shell.returncode is not None:
                    debug("*** Shell died for docker host '%s'!\n" % self.name)
                    self.shell = None
                    debug("*** Restarting Shell of docker host '%s'!\n" % self.name)
                    self.startShell()
            else:
                debug("*** Restarting Shell of docker host '%s'!\n" % self.name)
                self.startShell()
        else:
            error(
                "ERROR: Can't connect to Container '%s'' for docker host '%s'!\n"
                % (self.dins.id, self.name)
            )
            if self.shell:
                self.shell = None

    def _is_container_running(self):
        """Verify if container is alive"""
        container_list = self.dcli.containers(
            filters={"id": self.dins.id, "status": "running"}
        )
        if len(container_list) == 0:
            return False
        return True

    # MARK (Zuo): Use iproute2 instead of ifconfig to configure the IP address
    # of the default interface of the DockerHost.
    def setIP(self, ip, prefixLen=8, intf=None, **kwargs):
        """Set the IP address for an interface.
        intf: intf or intf name
        ip: IP address as a string
        prefixLen: prefix length, e.g. 8 for /8 or 16M addrs
        kwargs: any additional arguments for intf.setIP"""

        ifce = self.intf(intf)
        debug("Use iproute2 instead of ifconfig (used by Mininet).\n")
        if "/" in ip:
            ifce.ip, ifce.prefixLen = ip.split("/")
            ret = self.cmd("ip addr add {} dev {}".format(ip, ifce.name))
            return ret
        else:
            if prefixLen is None:
                raise Exception("No prefix length set for IP address %s" % (ip,))
            ifce.ip, ifce.prefixLen = ip, prefixLen
            ret = self.cmd("ip addr add {}/{} dev {}".format(ip, prefixLen, ifce.name))
            return ret


class APPContainer:

    """Application containers that should run inside a DockerHost.

    A wrapper class to hide the implementation details of used container
    runtime. For example, it should expose the same API for different container
    runtimes like Docker, LXC or CRI-O (If ComNetsEmu project decides to support
    them).
    """

    def __init__(self, name: str, dhost: str, dimage: str, dins, dcmd: str = None):
        """Create a APPContainer.

        :param name: Name of the APP container.
        :type name: str
        :param dhost: Name of the DockerHost on which APP container will be deployed.
        :type dhost: str
        :param dimage: Name of the image.
        :type dimage: str
        :param dins: The Docker container instance.
        :param dcmd: The Docker command.
        :type dcmd: str
        """
        self.name = name
        self.dhost = dhost
        self.dimage = dimage
        self.dcmd = dcmd if dcmd is not None else "/usr/bin/env sh"
        self.dins = dins

    def getCurrentStats(self):
        """Get decoded current stats of the Docker container."""
        return self.dins.stats(decode=False, stream=False)

    def getLogs(self):
        """Get logs from this container."""
        return self.dins.logs(timestamps=True).decode("utf-8")

    def _terminate(self):
        """APPContainer specific cleanups."""
        pass


# INFO: Following P4 related host and switch source codes are copied/modified
# from the official p4-tutorial repository
# (https://github.com/p4lang/tutorials).

# Copyright 2013-present Barefoot Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

P4_SWITCH_START_TIMEOUT = 10  # seconds
P4_SWITCH_STOP_TIMEOUT = 10


class P4DockerHost(DockerHost):
    """DockerHost with custom configuration to work with software P4 switches (BMv2)"""

    def config(self, **params):
        """Configure host"""
        r = super(Host, self).config(**params)

        # Diable RX and TX checksum offloading and disable scatter-gather
        # ON the default interface.
        for off in ["rx", "tx", "sg"]:
            cmd = "/sbin/ethtool --offload {} {} off".format(
                self.defaultIntf().name, off
            )
            self.cmd(cmd)

        # Disable IPv6
        self.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        self.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        self.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

        return r

    def describe(self):
        info("**********\n")
        output("Network configuration for P4 host: {}\n".format(self.name))
        output(
            "Default interface: {}\t IP: {}\t MAC:{}\n".format(
                self.defaultIntf().name,
                self.defaultIntf().IP(),
                self.defaultIntf().MAC(),
            )
        )
        info("**********\n")


# TODO:  <19-05-22, Zuo Xiang>
# 1. Cleanup the classes for P4Switch and P4RuntimeSwitch. Remove duplicated/unnecessary code


class P4Switch(Switch):
    """P4 virtual switch"""

    device_id = 0

    def __init__(
        self,
        name: str,
        sw_path: str = None,
        json_path: str = None,
        thrift_port: int = None,
        pcap_dump: bool = False,
        log_console: bool = False,
        log_file: str = None,
        device_id: int = None,
        enable_debugger: bool = False,
        **kwargs,
    ):
        """Init the P4 switch

        :param name: Name of the P4 switch
        :type name: str
        :param sw_path: The path of the switch binary to execute
        :type sw_path: str
        :param json_path: Path to the P4 compiled JSON configuration
        :type json_path: str
        :param thrift_port: The port number of the Thrift server
        :type thrift_port: int
        :param pcap_dump: Whether to save pcap logs to the disk
        :type pcap_dump: bool
        :param log_console: Whether to enable console logging
        :type log_console: bool
        :param log_file: The path of the switch logging file
        :type log_file: str
        :param device_id: The unique ID for the switch
        :type device_id: int
        :param enable_debugger: Whether to enable debugger
        :type enable_debugger: bool
        """

        if device_id:
            self.device_id = device_id
            P4Switch.device_id = max(P4Switch.device_id, device_id)
        else:
            self.device_id = P4Switch.device_id
            P4Switch.device_id += 1

        dpid = dpidToStr(self.device_id)
        kwargs.update(dpid=dpid)
        super().__init__(name, **kwargs)

        assert sw_path
        assert json_path
        # make sure that the provided sw_path is valid
        pathCheck(sw_path)
        # make sure that the provided JSON file exists
        if not os.path.isfile(json_path):
            error("Invalid JSON file.\n")
            exit(1)
        self.sw_path = sw_path
        self.json_path = json_path

        self.thrift_port = thrift_port
        if checkListeningOnPort(self.thrift_port):
            error(
                "%s cannot bind port %d because it is bound by another process\n"
                % (self.name, self.grpc_port)
            )
            exit(1)

        # TODO: Improve the handling of logging here.
        self.pcap_dump = pcap_dump
        self.enable_debugger = enable_debugger
        self.log_console = log_console
        if log_file is not None:
            self.log_file = log_file
        else:
            self.log_file = "/tmp/p4s.{}.log".format(self.name)

        self.nanomsg = "ipc:///tmp/bm-{}-log.ipc".format(self.device_id)

    @classmethod
    def setup(cls):
        pass

    def check_switch_started(self, pid):
        """While the process is running (pid exists), we check if the Thrift
        server has been started. If the Thrift server is ready, we assume that
        the switch was started successfully. This is only reliable if the Thrift
        server is started at the end of the init process"""
        while True:
            if not os.path.exists(os.path.join("/proc", str(pid))):
                return False
            if checkListeningOnPort(self.thrift_port):
                return True
            sleep(0.5)

    def start(self, controllers=None):
        """Start up a new P4 switch

        :param controllers:
        :type controllers: list
        """
        info("Starting P4 switch {}.\n".format(self.name))
        args = [self.sw_path]

        for port, intf in list(self.intfs.items()):
            if not intf.IP():
                args.extend(["-i", str(port) + "@" + intf.name])

        if self.pcap_dump:
            args.append("--pcap %s" % self.pcap_dump)
        if self.thrift_port:
            args.extend(["--thrift-port", str(self.thrift_port)])
        if self.nanomsg:
            args.extend(["--nanolog", self.nanomsg])
        args.extend(["--device-id", str(self.device_id)])
        # TODO: Why here device_id += 1? Handle the device_id in the __init__.
        P4Switch.device_id += 1
        args.append(self.json_path)
        if self.enable_debugger:
            args.append("--debugger")
        if self.log_console:
            args.append("--log-console")
        info(" ".join(args) + "\n")

        pid = None
        with tempfile.NamedTemporaryFile() as f:
            # self.cmd(' '.join(args) + ' > /dev/null 2>&1 &')
            self.cmd(
                " ".join(args) + " >" + self.log_file + " 2>&1 & echo $! >> " + f.name
            )
            pid = int(f.read())
        debug("P4 switch {} PID is {}.\n".format(self.name, pid))
        if not self.check_switch_started(pid):
            error("P4 switch {} did not start correctly.\n".format(self.name))
            exit(1)
        info("P4 switch {} has been started.\n".format(self.name))

    def stop(self):
        "Terminate P4 switch."
        self.cmd("kill %" + self.sw_path)
        self.cmd("wait")
        self.deleteIntfs()

    def describe(self):
        info("**********\n")
        output(
            "P4RuntimeSwitch name: {}, device_id: {}, dpid:{}, thrift_port: {}, grpc_port: {}\n".format(
                self.name, self.device_id, self.dpid, self.thrift_port, self.grpc_port
            )
        )
        info("**********\n")


class P4RuntimeSwitch(P4Switch):
    "BMv2 switch with gRPC support"
    next_grpc_port = 50051
    next_thrift_port = 9090

    def __init__(
        self,
        name,
        sw_path=None,
        json_path=None,
        grpc_port=None,
        thrift_port=None,
        pcap_dump=False,
        log_console=False,
        verbose=False,
        device_id=None,
        enable_debugger=False,
        log_file=None,
        **kwargs,
    ):
        if device_id is not None:
            self.device_id = device_id
            P4Switch.device_id = max(P4Switch.device_id, device_id)
        else:
            self.device_id = P4Switch.device_id
            P4Switch.device_id += 1

        dpid = dpidToStr(self.device_id)
        kwargs.update(dpid=dpid)
        Switch.__init__(self, name, **kwargs)

        assert sw_path
        self.sw_path = sw_path
        # make sure that the provided sw_path is valid
        pathCheck(sw_path)

        if json_path is not None:
            # make sure that the provided JSON file exists
            if not os.path.isfile(json_path):
                error("Invalid JSON file: {}\n".format(json_path))
                exit(1)
            self.json_path = json_path
        else:
            self.json_path = None

        if grpc_port is not None:
            self.grpc_port = grpc_port
        else:
            self.grpc_port = P4RuntimeSwitch.next_grpc_port
            P4RuntimeSwitch.next_grpc_port += 1

        if thrift_port is not None:
            self.thrift_port = thrift_port
        else:
            self.thrift_port = P4RuntimeSwitch.next_thrift_port
            P4RuntimeSwitch.next_thrift_port += 1

        if checkListeningOnPort(self.grpc_port):
            error(
                "%s cannot bind port %d because it is bound by another process\n"
                % (self.name, self.grpc_port)
            )
            exit(1)

        self.verbose = verbose
        self.pcap_dump = pcap_dump
        self.enable_debugger = enable_debugger
        self.log_console = log_console
        if log_file is not None:
            self.log_file = log_file
        else:
            self.log_file = "/tmp/p4s.{}.log".format(self.name)
        self.nanomsg = "ipc:///tmp/bm-{}-log.ipc".format(self.device_id)

    def check_switch_started(self, pid):
        for _ in range(P4_SWITCH_START_TIMEOUT * 2):
            if not os.path.exists(os.path.join("/proc", str(pid))):
                return False
            if checkListeningOnPort(self.grpc_port):
                return True
            sleep(0.5)

    def start(self, controllers=None):
        info("Starting P4 switch {}.\n".format(self.name))
        args = [self.sw_path]
        for port, intf in list(self.intfs.items()):
            if not intf.IP():
                args.extend(["-i", str(port) + "@" + intf.name])
        if self.pcap_dump:
            args.append("--pcap %s" % self.pcap_dump)
        if self.nanomsg:
            args.extend(["--nanolog", self.nanomsg])
        args.extend(["--device-id", str(self.device_id)])
        P4Switch.device_id += 1
        if self.json_path:
            args.append(self.json_path)
        else:
            args.append("--no-p4")
        if self.enable_debugger:
            args.append("--debugger")
        if self.log_console:
            args.append("--log-console")
        if self.thrift_port:
            args.append("--thrift-port " + str(self.thrift_port))
        if self.grpc_port:
            args.append("-- --grpc-server-addr 0.0.0.0:" + str(self.grpc_port))
        cmd = " ".join(args)
        info(cmd + "\n")

        pid = None
        with tempfile.NamedTemporaryFile() as f:
            self.cmd(cmd + " >" + self.log_file + " 2>&1 & echo $! >> " + f.name)
            pid = int(f.read())
        debug("P4 switch {} PID is {}.\n".format(self.name, pid))
        if not self.check_switch_started(pid):
            error("P4 switch {} did not start correctly.\n".format(self.name))
            exit(1)
        info("P4 switch {} has been started.\n".format(self.name))

    def describe(self):
        info("**********\n")
        output(
            "P4RuntimeSwitch name: {}, device_id: {}, dpid:{}, thrift_port: {}, grpc_port: {}\n".format(
                self.name, self.device_id, self.dpid, self.thrift_port, self.grpc_port
            )
        )
        info("**********\n")
