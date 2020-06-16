"""
About: ComNetsEmu Network Module.
"""

import http.server
import json
import os
import os.path
import shutil
import threading
from functools import partial
from time import sleep

import docker

from comnetsemu.cli import spawnXtermDocker
from comnetsemu.exceptions import InvalidDockerArgs
from comnetsemu.node import APPContainer, DockerHost
from mininet.log import debug, error, info
from mininet.net import Mininet
from mininet.term import cleanUpScreens, makeTerms
from mininet.util import BaseString

# ComNetsEmu version: should be consistent with README and LICENSE
VERSION = "0.1.12"

APPCONTAINERMANGER_MOUNTED_DIR = "/tmp/comnetsemu/appcontainermanger"


class Containernet(Mininet):
    """Network emulation with containerized network nodes."""

    def __init__(self, **params):
        """Create a Containernet object with the same parameters provided by
        Mininet.
        """
        self._appcontainers = list()
        Mininet.__init__(self, **params)

    def addDockerHost(self, name: str, **params):  # pragma: no cover
        """Wrapper for addHost method that adds a Docker container as a host.

        :param name: Name of the host.
        :type name: str
        """
        return self.addHost(name, cls=DockerHost, **params)

    def startTerms(self):  # pragma: no cover
        "Start a terminal for each node."
        if "DISPLAY" not in os.environ:
            error("Error starting terms: Cannot connect to display\n")
            return
        info("*** Running terms on %s\n" % os.environ["DISPLAY"])
        cleanUpScreens()
        self.terms += makeTerms(self.controllers, "controller")
        self.terms += makeTerms(self.switches, "switch")
        dhosts = [h for h in self.hosts if isinstance(h, DockerHost)]
        for d in dhosts:
            self.terms.append(spawnXtermDocker(d.name))
        rest = [h for h in self.hosts if h not in dhosts]
        self.terms += makeTerms(rest, "host")

    def addLinkNamedIfce(self, src, dst, *args, **kwargs):  # pragma: no cover
        """Add a link with two named interfaces.
           - Name of interface 1: src-dst
           - Name of interface 2: dst-src
        """
        # Accept node objects or names
        src = src if not isinstance(src, BaseString) else self[src]
        dst = dst if not isinstance(dst, BaseString) else self[dst]
        self.addLink(
            src,
            dst,
            intfName1="-".join((src.name, dst.name)),
            intfName2="-".join((dst.name, src.name)),
            *args,
            **kwargs,
        )


class APPContainerManagerRequestHandler(http.server.BaseHTTPRequestHandler):
    """Basic implementation of a REST API for app containers.

    Python's built-in http server only does basic security checks and this class
    has basic and limited sanity checks on the requests. Designed only for
    teaching.
    """

    _container_resource_path = "/containers"

    def __init__(self, appcontainermanager, enable_log=True, *args, **kargs):
        self.mgr = appcontainermanager
        self.enable_log = enable_log
        super(APPContainerManagerRequestHandler, self).__init__(*args, **kargs)

    def _send_bad_request(self):
        self.send_response(400)
        self.end_headers()

    def log_message(self, format, *args):
        if not self.enable_log:
            return
        else:  # pragma no cover
            super(APPContainerManagerRequestHandler, self).log_message(format, *args)

    def do_GET(self):
        if self.path == self._container_resource_path:
            self.send_response(200)
            self.end_headers()
            ret = json.dumps(self.mgr.getAllContainers()).encode("utf-8")
            self.wfile.write(ret)
        else:
            self._send_bad_request()

    @staticmethod
    def _post_sanity_check(post_dict):
        # Check for essential keys.
        for k in ["name", "dhost", "dimage", "dcmd", "docker_args"]:
            if k not in post_dict:
                return False
        else:
            return True

    def do_POST(self):
        """Create a new APP container."""
        if self.path == self._container_resource_path:
            content_length = int(self.headers.get("content-length", 0))
            if content_length == 0:
                self._send_bad_request()
            else:
                post_data = self.rfile.read(content_length).decode("utf-8")
                container_para = json.loads(post_data)
                if not self._post_sanity_check(container_para):
                    self._send_bad_request()
                else:
                    self.mgr.addContainer(**container_para)
                    self.send_response(200)
                    self.end_headers()
        else:
            self._send_bad_request()

    def _delete_sanity_check(self, container_name):
        # Check if container exists.
        c = self.mgr.getContainerInstance(container_name, None)
        return True if c else False

    def do_DELETE(self):
        paths = os.path.split(self.path)
        if len(paths) == 2 and paths[0] == self._container_resource_path:
            container_name = paths[1]
            if not self._delete_sanity_check(container_name):
                self._send_bad_request()
            else:
                self.mgr.removeContainer(container_name)
                self.send_response(200)
                self.end_headers()
        else:
            self._send_bad_request()


class APPContainerManager:
    """Manager for application containers (sibling containers) deployed on
    Mininet hosts.

    - To make is simple. It uses docker-py APIs to manage internal containers
      from host system.

    - Internal methods (starts with an underscore) should be documented after
      tests and before stable releases.

    Ref:
        [1] https://docker-py.readthedocs.io/en/stable/containers.html
    """

    reserved_docker_args = [
        "init",
        "tty",
        "detach",
        "labels",
        "security_opt",
        "cgroup_parent",
        "network_mode",
    ]

    docker_args_default = {
        "init": True,
        "tty": True,  # -t
        "detach": True,  # -d
        # Used for cleanups
        "labels": {"comnetsemu": "dockercontainer"},
        # Required for CRIU checkpoint
        "security_opt": ["seccomp:unconfined"],
    }

    docker_volumes_default = {
        # Shared directory in host OS
        APPCONTAINERMANGER_MOUNTED_DIR: {
            "bind": APPCONTAINERMANGER_MOUNTED_DIR,
            "mode": "rw",
        }
    }

    # Default delay between tries for Docker API
    retry_delay_secs = 0.1

    def __init__(self, net: Mininet):
        """Init the APPContainerManager.

        :param net (Mininet): The mininet object, used to manage hosts via
        Mininet's API.
        """
        self.net = net
        self.dclt = docker.from_env()

        # Following resources can be shared by main and httpd threads.
        # A simple lock is used.
        self._container_queue_lock = threading.Lock()
        self._container_queue = list()
        # Fast search for added containers.
        self._name_container_map = dict()

        self._http_server_started = False
        self._http_server_thread = None

        os.makedirs(APPCONTAINERMANGER_MOUNTED_DIR, exist_ok=True)

    def _createContainer(self, name, dhost, dimage, dcmd, docker_args):
        """Create a Docker container."""
        if "volumes" in docker_args:
            debug(
                f"Update the default volumes {self.docker_volumes_default} to the already given volumes config.\n"
            )
            docker_args["volumes"].update(self.docker_volumes_default)
        for key in self.reserved_docker_args:
            if key in docker_args:
                error(
                    f"Given argument: {key} is invalid. This key is reserved by the APPContainerManager for internal usage."
                )
                raise InvalidDockerArgs

        docker_args.update(self.docker_args_default)
        docker_args["name"] = name
        docker_args["image"] = dimage
        docker_args["cgroup_parent"] = "/docker/{}".format(dhost.dins.id)
        docker_args["command"] = dcmd
        docker_args["network_mode"] = "container:{}".format(dhost.dins.id)

        ret = self.dclt.containers.create(**docker_args)
        return ret

    def _waitContainerStart(self, name):  # pragma: no cover
        """Wait for container to start up running"""
        while not self._getDockerIns(name):
            debug("Failed to get container:%s" % (name))
            sleep(self.retry_delay_secs)
        dins = self._getDockerIns(name)

        while not dins.attrs["State"]["Running"]:
            sleep(self.retry_delay_secs)
            dins.reload()  # refresh information in 'attrs'

    def _waitContainerRemoved(self, name):  # pragma: no cover
        """Wait for container to be removed"""
        while self._getDockerIns(name):
            sleep(self.retry_delay_secs)

    def _getDockerIns(self, name):
        """Get the APPContainer instance by name.

        :param name (str): Name of the container
        """
        try:
            dins = self.dclt.containers.get(name)
        except docker.errors.NotFound:
            return None
        return dins

    def getContainerInstance(self, name: str, default=None) -> APPContainer:
        """Get the APPContainer instance with the given name.

        :param name: The name of the given container.
        :type name: str
        :param default: The default return value if not found.
        :rtype: APPContainer
        """
        with self._container_queue_lock:
            for c in self._container_queue:
                if c.name == name:
                    return c
            else:
                return default

    def getContainersDhost(self, dhost: str) -> list:
        """Get containers deployed on the given DockerHost.

        :param dhost: Name of the DockerHost.
        :type dhost: str
        :return: A list of APPContainer instances on given DockerHost.
        :rtype: list
        """
        with self._container_queue_lock:
            clist = [c.name for c in self._container_queue if c.dhost == dhost]
            return clist

    def getAllContainers(self) -> list:
        """Get a list of names of all containers in current container queue.

        :rtype: list
        """
        with self._container_queue_lock:
            return [c.name for c in self._container_queue]

    def addContainer(
        self,
        name: str,
        dhost: str,
        dimage: str,
        dcmd: str,
        docker_args: dict = None,
        wait: bool = True,
    ) -> APPContainer:
        """Create and run a new container inside a Mininet DockerHost.

        :param name: Name of the container.
        :type name: str
        :param dhost: Name of the host used for deployment.
        :type name: str
        :param dimage: Name of the docker image.
        :type dimage: str
        :param dcmd: Command to run after the creation.
        :type dcmd: str
        :param docker_args: All other keyword arguments supported by Docker-py.
            e.g. CPU and memory related limitations.
            Some parameters are overriden for APPContainerManager's functionalities.
        :type docker_args: dict
        :param wait: Wait until the container has the running state if True.
        :type wait: bool

        Check cls.docker_args_default.

        :return: Added APPContainer instance or None if the creation process failed.
        :rtype: APPContainer
        """
        container = None
        if not docker_args:
            docker_args = dict()
        dhost = self.net.get(dhost)
        with self._container_queue_lock:
            dins = self._createContainer(name, dhost, dimage, dcmd, docker_args)
            dins.start()
            if wait:
                self._waitContainerStart(name)
            container = APPContainer(name, dhost.name, dimage, dins)
            self._container_queue.append(container)
            self._name_container_map[container.name] = container
            self.net._appcontainers.append(name)
            return container

    def removeContainer(self, name: str, wait: bool = True):
        """Remove the APP container with the given name.

        :param name: Name of the to be removed container.
        :type name: str
        :param wait: Wait until the container is fully removed if True.
        :type wait: bool
        """
        with self._container_queue_lock:
            container = self._name_container_map.get(name, None)
            # The container could be already removed by the user via CLI or
            # other approaches, raise the exception to let user handle this
            # situation.
            if not container:
                raise ValueError(f"Can not find container with name: {container}")

            container.dins.remove(force=True)
            if wait:
                self._waitContainerRemoved(container.name)
            self._container_queue.remove(container)
            self.net._appcontainers.remove(name)
            del self._name_container_map[name]

    @staticmethod
    def _calculate_cpu_percent(stats):
        """Calculate the CPU usage in percent with given stats JSON data"""
        cpu_count = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
        cpu_percent = 0.0
        cpu_delta = float(stats["cpu_stats"]["cpu_usage"]["total_usage"]) - float(
            stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = float(stats["cpu_stats"]["system_cpu_usage"]) - float(
            stats["precpu_stats"]["system_cpu_usage"]
        )
        if system_delta > 0.0:
            cpu_percent = cpu_delta / system_delta * 100.0 * cpu_count

        if cpu_percent > 100:  # pragma: no cover
            cpu_percent = 100

        return cpu_percent

    def monResourceStats(
        self, name: str, sample_num: int = 3, sample_period: float = 1.0
    ) -> list:
        """Monitor the resource stats of a container within the given name.
        This function measure the CPU and memory usages sample_num times and
        sleep for sample_period between each time. All measurement results are
        returned as a list.

        :param container: Name of the container
        :type container: str
        :param sample_num: Number of samples.
        :type sample_num: int
        :param sample_period: Sleep period for each sample
        :type sample_period: float

        :return: A list of resource usages. Each item is a tuple (cpu_usg, mem_usg)
        :rtype: list
        :raise ValueError: container is not found
        """

        container = self._name_container_map.get(name, None)
        if not container:
            raise ValueError(f"Can not found container with name: {container}")

        n = 0
        usages = list()
        while n < sample_num:
            stats = container.getCurrentStats()
            mem_stats = stats["memory_stats"]
            mem_usg = mem_stats["usage"] / (1024 ** 2)
            cpu_usg = self._calculate_cpu_percent(stats)
            usages.append((cpu_usg, mem_usg))
            sleep(sample_period)
            n += 1

        return usages

    # BUG: Checkpoint inside container breaks the networking of outside
    # container if container networking mode is used.
    # def checkpoint(self, container: str) -> str:
    #     container = self._name_container_map.get(container, None)
    #     if not container:
    #         raise ValueError(f"Can not found container with name: {container}")
    #     ckpath = os.path.join(APPCONTAINERMANGER_MOUNTED_DIR, f"{container.name}")
    #     # MARK: Docker-py does not provide API for checkpoint and restore,
    #     # Docker CLI is directly used with subprocess as a temp workaround.
    #     subprocess.run(split(
    #         f"docker checkpoint create --checkpoint-dir={ckpath} {container.name} {container.name}"
    #     ),
    #                    check=True,
    #                    stdout=subprocess.DEVNULL,
    #                    stderr=subprocess.DEVNULL)

    #     return ckpath

    def _runHTTPServer(self, ip_addr, port, enable_log):
        """Generate HTTPServer with partial parameters and run it forever."""
        handler = partial(APPContainerManagerRequestHandler, self, enable_log)
        httpd = http.server.HTTPServer((ip_addr, port), handler)
        info(f"Start REST API server on address: {ip_addr}:{port}.\n")
        httpd.serve_forever()

    def runRESTServerThread(
        self, ip: str, port: int = 8000, enable_log: bool = True
    ) -> None:
        """Run the REST API server in a separate daemon thread.
        threading is used to avoid blocking the main thread in the emulation
        scripts. Since to be performed operation is more IO-bounded and this
        server should have no impact on the concurrency approach of main thread,
        the threading with a Lock is used instead of multi-processing or
        asyncio.

        :param ip: Listening IP address.
        :type ip: str
        :param port: Port number.
        :type port: int
        :param enable_log: Print logs using stdout if True.
        :type enable_log: bool
        """
        self._http_server_started = True
        self._http_server_thread = threading.Thread(
            target=self._runHTTPServer, args=(ip, port, enable_log)
        )
        # It will die if all non-daemon threads (including main) exist.
        self._http_server_thread.daemon = True
        self._http_server_thread.start()

    def stop(self):
        """Stop the APPContainerManager."""
        if len(self._container_queue) > 0:
            info(
                "Stop {} containers in the App container queue: {}\n".format(
                    len(self._container_queue),
                    ", ".join((c.name for c in self._container_queue)),
                )
            )

            # Avoid missing delete internal containers manually before stop
            for c in self._container_queue:
                c._terminate()
                c.dins.remove(force=True)

        self.dclt.close()
        shutil.rmtree(APPCONTAINERMANGER_MOUNTED_DIR)


class VNFManager(APPContainerManager):
    """App container for Virtualized Network Functions"""

    pass
