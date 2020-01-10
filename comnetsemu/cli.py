# flake8: noqa
"""
About: ComNetsEmu simple command-line interface

This module sub-class the Mininet's CLI class to add some ComNetsEmu's specific
properly for DockerHost instances.
commands, and also add fixes to some Mininet's default methods to make it work

ISSUE: Current approach has too much Mininet codes included... Make it dependent
       on the upstream. A better solution should be added.
"""

import errno
import select
import shlex
import subprocess
from cmd import Cmd
from select import POLLIN, poll

from comnetsemu.node import DockerHost
from mininet.cli import CLI, isReadable
from mininet.log import error, output
from mininet.term import makeTerms
from mininet.util import quietRun


class CLI(CLI):  # pylint: disable=function-redefined
    """Mininet's CLI subclass with support for Docker containers."""

    helpStr = (
        "You can send commands to Docker hosts with the same method of Mininet.\n"
        "You can open xterm(s) to have interactive shells of Docker hosts"
        "with xterm command:\n"
        "  mininet> xterm h1 h2\n"
    )

    def do_help(self, line):
        "Describe available CLI commands."
        Cmd.do_help(self, line)

        if line == "":
            output("\n*** Mininet CLI usage:\n")
            output(super(CLI, self).helpStr)

            output("*** ComNetsEmu CLI usage:\n")
            output(self.helpStr)

    def do_appcontainers(self, _):
        """List deployed app containers."""
        appcontainers = " ".join(self.mn._appcontainers)
        output("deployed app containers are: \n%s\n" % appcontainers)

    def do_xterm(self, line, term="xterm"):
        """Spawn xterm(s) for the given node(s).
           Usage: xterm node1 node2 ..."""
        args = line.split()
        if not args:
            error("usage: %s node1 node2 ...\n" % term)
        else:
            for arg in args:
                if arg not in self.mn:
                    error("node '%s' not in network\n" % arg)
                else:
                    node = self.mn[arg]
                    if isinstance(node, DockerHost):
                        self.mn.terms.append(spawnXtermDocker(node))
                    else:
                        self.mn.terms += makeTerms([node], term=term)

    def waitForNode(self, node):
        """Wait for a node to finish, and print its output.

        - Force to break the while loop if KeyboardInterrupt is detected.
        """
        if not isinstance(node, DockerHost):
            super(CLI, self).waitForNode(node)
        else:
            # Pollers
            nodePoller = poll()
            nodePoller.register(node.stdout)
            bothPoller = poll()
            bothPoller.register(self.stdin, POLLIN)
            bothPoller.register(node.stdout, POLLIN)
            if self.isatty():
                # Buffer by character, so that interactive
                # commands sort of work
                quietRun("stty -icanon min 1")
            while True:
                try:
                    bothPoller.poll()
                    # XXX BL: this doesn't quite do what we want.
                    if False and self.inputFile:
                        key = self.inputFile.read(1)
                        if key != "":
                            node.write(key)
                        else:
                            self.inputFile = None
                    if isReadable(self.inPoller):
                        key = self.stdin.read(1)
                        node.write(key)
                    if isReadable(nodePoller):
                        data = node.monitor()
                        output(data)
                    if not node.waiting:
                        break
                except KeyboardInterrupt:
                    # There is an at least one race condition here, since it's
                    # possible to interrupt ourselves after we've read data but
                    # before it has been printed.
                    #  TODO:  <08-06-19, Zuo> Send Interrupt to correct process
                    #  in DockerHost container#
                    error("The command is not terminated. Please kill it manually\n")
                    node.sendInt()
                    break
                except select.error as e:
                    # pylint: disable=unpacking-non-sequence
                    errno_, errmsg = e.args
                    # pylint: enable=unpacking-non-sequence
                    if errno_ != errno.EINTR:
                        error("select.error: %s, %s" % (errno_, errmsg))
                        error(
                            "The command is not terminated. Please kill it manually\n"
                        )
                        node.sendInt()
                        break

    def default(self, line):
        """Called on an input line when the command prefix is not recognized

        - Show warning message if first parameter is a DockerHost
        """
        first, _, _ = self.parseline(line)
        if first in self.mn:
            node = self.mn[first]
            if isinstance(node, DockerHost):
                print(
                    "\n[WARNING] Run command in DockerHost instance with this "
                    "method currently can not handle signals correctly.\n"
                    "This means use ctrl+c to stop the process with SIGINT can "
                    "not stop the process inside DockerHost instance. The "
                    "command to use should terminate gracefully automatically.\n"
                    "\nFor example:"
                    "'ping -c 3 DEST_IP' will terminate gracefully. "
                    "'ping DEST_IP' will not terminate gracefully with ctrl+c, "
                    "the process is still running in the DockerHost container.\n"
                    "Please use 'xterm' command to attach to a running "
                    "DockerHost in a separate xterm to run commands with signals properly handled.\n"
                    "\n"
                )

        super(CLI, self).default(line)


def spawnXtermDocker(dcontainer_name: str):
    """Spawn the xterm and attach to a Docker container with docker exec -it
    container. Bash is used as the interactive shell.

    :param dcontainer_name (str): Name of a Docker container.
    """
    title = '"dockercontainer:%s"' % dcontainer_name
    params = {"title": title, "name": dcontainer_name, "shell": "bash"}
    cmd = "xterm -title {title} -e 'docker exec -it {name} {shell}'".format(**params)

    term = subprocess.Popen(shlex.split(cmd))
    return term
