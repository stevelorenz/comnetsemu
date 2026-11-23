from mininet.net import Mininet
from mininet.node import RemoteController
from nullswitch import NullSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

import json
import sys

HOSTFIL = "../ryu_output/hosts.json"
LINK = "../ryu_output/links.json"

def fetchTopology(base_url):
    return

def normalize():
    return

def diff(phys, twin):
    missmatches = []
    return missmatches

#ferdig! returnerer True hvis det ikke er noe galt
def report(missmatches):
    return (missmatches.len() == 0)


def validate():
    fetchTopology()
    normalize()
    missmatches = diff()
    report(missmatches)


def main():
    return