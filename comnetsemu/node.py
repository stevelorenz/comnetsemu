"""
About: ComNetsEmu Node
"""

import os
import pty
import select
import shlex
import time

import docker

from comnetsemu.exceptions import InvalidDockerArgs
from mininet.log import debug, error, info, warn
from mininet.node import Host


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
        """ Stop docker container """
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

    # MARK(Zuo): This is a temporary workaround. I will submit an issue to upstream
    # Mininet project to modify the current Intf.setIP() method.
    def setIP(self, ip, prefixLen=8, intf=None, **kwargs):
        """Set the IP address for an interface.
           intf: intf or intf name
           ip: IP address as a string
           prefixLen: prefix length, e.g. 8 for /8 or 16M addrs
           kwargs: any additional arguments for intf.setIP"""

        ifce = self.intf(intf)
        ret = ifce.setIP(ip, prefixLen, **kwargs)
        if ret.startswith("ifconfig: bad"):
            # warn("\nFailed to set IP address with ifconfig\n")
            debug("Use iproute2 instead of ifconfig (used by Mininet).\n")
            if "/" in ip:
                ifce.ip, ifce.prefixLen = ip.split("/")
                ret = self.cmd("ip addr add {} dev {}".format(ip, ifce.name))
            else:
                if prefixLen is None:
                    raise Exception("No prefix length set for IP address %s" % (ip,))
                ifce.ip, ifce.prefixLen = ip, prefixLen
                ret = self.cmd(
                    "ip addr add {}/{} dev {}".format(ip, prefixLen, ifce.name)
                )
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
