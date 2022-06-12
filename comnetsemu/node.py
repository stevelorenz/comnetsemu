#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""

__ https://github.com/mininet/mininet/blob/master/mininet/node.py

This module is an extension of `mininet.node`__ with additional and customized nodes.
"""

import os
import pty
import select
import shlex
import tempfile
import time
import socket

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

    def __init__(self, name: str, dhost: str, dimage: str, dins, dcmd: str = None):
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


class P4Switch(Switch):
    """P4Switch: BMv2 simple_switch

    This is the `simple_switch` target (https://github.com/p4lang/behavioral-model/blob/main/targets/README.md)
    provided by bmv2.

    :param name: Name of the switch
    :type name: str
    :param json_path: Path to the P4 compiled JSON output
    :type json_path: str
    :param thrift_port: Port of the Thrift server
    :type thrift_port: int
    :param sw_path: Switch binary to execute. Must be available in system $PATH.
    :type sw_path: str
    :param log_file: The path of the logging file
    :type log_file: str
    :param pcap_dump: Whether to dump pcap files to disk
    :type pcap_dump: bool
    :param log_console: Whether to log into console
    :type log_console: bool
    :param device_id: Unique ID for the switch
    :type device_id: int
    :param enable_debugger: Whether to enable debugger
    :type enable_debugger: bool
    """

    device_id = 0

    def __init__(
        self,
        name: str,
        json_path: str,
        thrift_port: int,
        sw_path: str = "simple_switch",
        log_file: str = "",
        pcap_dump: bool = False,
        log_console: bool = False,
        device_id: int = 0,
        enable_debugger: bool = False,
        **kwargs,
    ):
        # Assign the device_id automatically
        if not device_id:
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
            error("Invalid JSON file:{}.\n".format(json_path))
            exit(1)
        self.sw_path = sw_path
        self.json_path = json_path
        self.log_file = log_file
        if not self.log_file:
            self.log_file = "/tmp/p4s.{}.log".format(self.name)
        self.thrift_port = thrift_port
        self.pcap_dump = pcap_dump
        self.enable_debugger = enable_debugger
        self.log_console = log_console
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
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(("localhost", self.thrift_port))
            if result == 0:
                return True

    def start(self, controllers):
        "Start up a new P4 switch"
        info("Starting P4 switch {}.\n".format(self.name))
        args = [self.sw_path]
        for port, intf in list(self.intfs.items()):
            if not intf.IP():
                args.extend(["-i", str(port) + "@" + intf.name])
        if self.pcap_dump:
            args.append("--pcap")
            # args.append("--useFiles")
        if self.thrift_port:
            args.extend(["--thrift-port", str(self.thrift_port)])
        if self.nanomsg:
            args.extend(["--nanolog", self.nanomsg])
        args.extend(["--device-id", str(self.device_id)])
        args.append(self.json_path)
        if self.enable_debugger:
            args.append("--debugger")
        if self.log_console:
            args.append("--log-console")
        info(" ".join(args) + "\n")

        pid = None
        with tempfile.NamedTemporaryFile() as f:
            # MARK: This way of running switch binary can not support running xterm on the switch
            self.cmd(
                " ".join(args) + " >" + self.log_file + " 2>&1 & echo $! >> " + f.name
            )
            pid = int(f.read())
        debug("P4 switch {} PID is {}.\n".format(self.name, pid))
        sleep(1)
        if not self.check_switch_started(pid):
            error(
                "P4 switch {} did not start correctly."
                "Check the switch log file.\n".format(self.name)
            )
            exit(1)
        info("P4 switch {} has been started.\n".format(self.name))

    def stop(self):
        "Terminate P4 switch."
        self.cmd("kill %" + self.sw_path)
        self.cmd("wait")
        self.deleteIntfs()

    def attach(self, intf):
        "Connect a data port"
        assert 0

    def detach(self, intf):
        "Disconnect a data port"
        assert 0

    def describe(self):
        info("**********\n")
        output(
            "P4Switch name: {}, device_id: {}, dpid:{}, thrift_port: {}\n".format(
                self.name, self.device_id, self.dpid, self.thrift_port
            )
        )
        info("**********\n")


class P4RuntimeSwitch(P4Switch):
    """BMv2 switch with gRPC support.


    :param name: Name of the switch
    :type name: str
    :param json_path: Path to the P4 compiled JSON output
    :type json_path: str
    :param thrift_port: Port of the Thrift server
    :type thrift_port: int
    :param grpc_port: Port of the P4Rutime gRPC server
    :type grpc_port: int
    :param sw_path: Switch binary to execute. Must be available in system $PATH.
    :type sw_path: str
    :param log_file: The path of the logging file
    :type log_file: str
    :param pcap_dump: Whether to dump pcap files to disk
    :type pcap_dump: bool
    :param log_console: Whether to log into console
    :type log_console: bool
    :param device_id: Unique ID for the switch
    :type device_id: int
    :param enable_debugger: Whether to enable debugger
    :type enable_debugger: bool
    """

    def __init__(
        self,
        name: str,
        json_path: str,
        thrift_port: int,
        grpc_port: int,
        sw_path: str = "simple_switch_grpc",
        **kwargs,
    ):
        self.grpc_port = grpc_port
        if checkListeningOnPort(grpc_port):
            raise ConnectionRefusedError(
                f"Switch {name} cannot bind gRPC port {grpc_port} because the port is already used."
            )

        super(P4RuntimeSwitch, self).__init__(
            name, json_path, thrift_port, sw_path=sw_path, **kwargs
        )

    def check_switch_started(self, pid):
        for _ in range(P4_SWITCH_START_TIMEOUT * 2):
            if not os.path.exists(os.path.join("/proc", str(pid))):
                return False
            if checkListeningOnPort(self.grpc_port):
                return True
            sleep(0.5)

    def start(self, controllers=None):
        info("Starting P4RuntimeSwitch {}.\n".format(self.name))
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
        debug("P4RuntimeSwitch {} PID is {}.\n".format(self.name, pid))
        if not self.check_switch_started(pid):
            error("P4RuntimeSwitch {} did not start correctly.\n".format(self.name))
            exit(1)
        info("P4RuntimeSwitch {} has been started.\n".format(self.name))

    def describe(self):
        info("**********\n")
        output(
            "P4RuntimeSwitch name: {}, device_id: {}, dpid:{}, thrift_port: {}, grpc_port: {}\n".format(
                self.name, self.device_id, self.dpid, self.thrift_port, self.grpc_port
            )
        )
        info("**********\n")
