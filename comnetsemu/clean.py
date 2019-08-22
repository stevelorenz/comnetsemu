#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: ComNetsEmu cleanup
"""

import re
import subprocess
from shlex import split
import shutil

import docker
from mininet.log import LEVELS, debug, error, info
from comnetsemu.net import VNFMANGER_MOUNTED_DIR


def sh(cmd, check=True):
    ret = subprocess.run(split(cmd), check=check,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return ret.stdout.decode('utf-8')


def cleanup():
    info("-" * 80 + "\n"+"*** Run ComNetsEmu's cleanups\n" + "-" * 80 + "\n")
    info("*** Run mininet's cleanups\n")
    subprocess.run(["mn", "-c"], check=True)
    cleanup_docker_containers()
    cleanup_netdevs()
    info("*** Remove temp directories\n")
    shutil.rmtree(VNFMANGER_MOUNTED_DIR, ignore_errors=True)


def cleanup_docker_containers():
    info("*** Run docker container cleanups\n")
    client = docker.from_env()
    containers = client.containers.list(all=True)
    docker_hosts = list()
    internal_containers = list()
    for c in containers:
        _type = c.labels.get("comnetsemu", None)
        if not _type:
            continue
        if _type == "dockerhost":
            docker_hosts.append(c)
        elif _type == "dockercontainer":
            internal_containers.append(c)

    if docker_hosts:
        info("Force remove all running DockerHost instances: {}\n".format(
            ", ".join([c.name for c in docker_hosts])))
        for c in docker_hosts:
            c.remove(force=True)

    if internal_containers:
        info("Force remove all running internal Docker containers: {}\n".format(
            ", ".join([c.name for c in internal_containers])))
        for c in internal_containers:
            c.remove(force=True)

    client.close()


def cleanup_netdevs():
    """ISSUE: Maybe too aggressive."""
    info(
        r"*** Remove all network devices in /sys/class/net/ with the pattern [a-zA-Z]*[\d]+-[a-zA-Z]*[\d]+ \n")
    links = sh("ip link show")
    ret = re.findall(r"[a-zA-Z]*[\d]+-[a-zA-Z]*[\d]+", links)
    if ret:
        for link in ret:
            sh("ip link delete {}".format(link), check=False)
