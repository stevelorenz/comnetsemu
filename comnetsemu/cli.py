"""
About: ComNetsEmu simple command-line interface


This sub-class also fixes some bugs when using Mininet's CLI for DockerHost:

-
"""

import shlex
import subprocess
from cmd import Cmd

from comnetsemu.node import DockerHost
from mininet.cli import CLI
from mininet.log import error, info, output


class CLI(CLI):

    helpStr = (
        "You can send commands to Docker hosts with the same method of Mininet.\n"
        "You can open xterm(s) to have interactive shells of Docker hosts"
        "with attach command:\n"
        "  mininet> attach h1 h2\n"
    )

    def do_help(self, line):
        "Describe available CLI commands."
        Cmd.do_help(self, line)

        if line == "":
            output("\n*** Mininet CLI usage:\n")
            output(super(CLI, self).helpStr)

            output("*** ComNetsEmu CLI usage:\n")
            output(self.helpStr)

    @staticmethod
    def spawn_xterm(dhost):
        """Make the xterm and attach to dhost with docker exec -it container

        :param dhost (str): Name of the docker host
        """
        title = '"dockerhost:%s"' % dhost
        params = {
            "title": title,
            "name": "mn.%s" % dhost,
            "shell": "/usr/bin/env sh"
        }
        cmd = "xterm -title {title} -e 'docker exec -it {name} {shell}'".format(
            **params)
        try:
            subprocess.Popen(shlex.split(cmd))
        except OSError as e:
            error("Can not open xterm with error: %s" % str(e))

    def do_attach(self, line):
        """Spawn xterm(s) and attach to Docker host(s). Similar to xterm command
        in Mininet but for DockerHost instances
        Usage: attach node1 node2 ..."""
        dhosts = line.split()
        if not dhosts:
            error("Usage: attach node1 node2 ...\n")
        else:
            for dhost in dhosts:
                ins = self.mn.get(dhost)
                if not ins or not isinstance(ins, DockerHost):
                    error("Attach command should be used for DockerHost"
                          "instances\n")
                    info("For Mininet's host, use xterm instead.\n")
                else:
                    self.spawn_xterm(dhost)
