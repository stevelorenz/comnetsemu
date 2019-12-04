#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# vim:fenc=utf-8
"""
About: Basic tests for functionalities of OpenVirteX (OVX)

Please run OpenVirteX and SDN controller in SEPARATE SHELLS (for monitoring the
outputs) before running this example program with:

$ bash ~/comnetsemu_dependencies/ovx-0.0-MAINT/OpenVirteX/scripts/ovx.sh
$ bash ../util/run_simple_switch.sh

Ref  : OpenVirteX Official Tutorial
       https://openvirtex.com/getting-started/tutorial/
"""

import os
import os.path as path
from shlex import split as sh_split
from subprocess import check_output

from comnetsemu.net import Containernet
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import error, info, setLogLevel
from mininet.node import RemoteController

# Same parameters are used in ../util/run_simple_switch.sh
SDN_CONTROLLER_IP = "127.0.0.1"
SDN_CONTROLLER_PORT = 10000

CORES = {
    "SEA": {"dpid": "000000000000010%s"},
    "SFO": {"dpid": "000000000000020%s"},
    "LAX": {"dpid": "000000000000030%s"},
    "ATL": {"dpid": "000000000000040%s"},
    "IAD": {"dpid": "000000000000050%s"},
    "EWR": {"dpid": "000000000000060%s"},
    "SLC": {"dpid": "000000000000070%s"},
    "MCI": {"dpid": "000000000000080%s"},
    "ORD": {"dpid": "000000000000090%s"},
    "CLE": {"dpid": "0000000000000a0%s"},
    "IAH": {"dpid": "0000000000000b0%s"},
}

FANOUT = 4

OVXCTL_DIR = path.join(
    path.expanduser("~"), "comnetsemu_dependencies/ovx-0.0-MAINT/OpenVirteX/utils"
)


def test_ovx():
    try:
        ip = "127.0.0.1"
        port = 6633

        info("*** Add remote controller\n")
        c = RemoteController("c", ip=ip, port=port)
        net = Containernet(
            autoStaticArp=True, autoSetMacs=True, controller=None, link=TCLink
        )
        net.addController(c)
        info("*** Add switches, hosts and links \n")
        # Add core switches
        cores = {}
        for switch in CORES:
            cores[switch] = net.addSwitch(switch, dpid=(CORES[switch]["dpid"] % "0"))

        # Add hosts and connect them to their core switch
        for switch in CORES:
            for count in range(1, FANOUT + 1):
                # Add hosts
                host = "h_%s_%s" % (switch, count)
                ip = "10.0.0.%s" % count
                mac = CORES[switch]["dpid"][4:] % count
                h = net.addDockerHost(host, dimage="dev_test", ip=ip, mac=mac)
                # Connect hosts to core switches
                net.addLink(cores[switch], h)

        # Connect core switches
        net.addLink(cores["SFO"], cores["SEA"])
        net.addLink(cores["SEA"], cores["SLC"])
        net.addLink(cores["SFO"], cores["LAX"])
        net.addLink(cores["LAX"], cores["SLC"])
        net.addLink(cores["LAX"], cores["IAH"])
        net.addLink(cores["SLC"], cores["MCI"])
        net.addLink(cores["MCI"], cores["IAH"])
        net.addLink(cores["MCI"], cores["ORD"])
        net.addLink(cores["IAH"], cores["ATL"])
        net.addLink(cores["ORD"], cores["ATL"])
        net.addLink(cores["ORD"], cores["CLE"])
        net.addLink(cores["ATL"], cores["IAD"])
        net.addLink(cores["CLE"], cores["IAD"])
        net.addLink(cores["CLE"], cores["EWR"])
        net.addLink(cores["EWR"], cores["IAD"])

        info("*** Start network... \n")
        net.start()
        print(
            "Hosts configured with IPs, switches pointing to OpenVirteX at %s:%s"
            % (ip, port)
        )

        info("[OVX] Create a virtual network between SEA and LAX\n")
        wd = os.getcwd()
        os.chdir(OVXCTL_DIR)
        commands = [
            # Create virtual networks
            "python2 ovxctl.py createNetwork tcp:{}:{} 10.0.0.0 16".format(
                SDN_CONTROLLER_IP, SDN_CONTROLLER_PORT
            ),
            # Create virtual switches
            "python2 ovxctl.py -n createSwitch 1 00:00:00:00:00:00:01:00",
            "python2 ovxctl.py -n createSwitch 1 00:00:00:00:00:00:02:00",
            "python2 ovxctl.py -n createSwitch 1 00:00:00:00:00:00:03:00",
            # Create virtual ports
            "python2 ovxctl.py -n createPort 1 00:00:00:00:00:00:01:00 1",
            "python2 ovxctl.py -n createPort 1 00:00:00:00:00:00:01:00 5",
            "python2 ovxctl.py -n createPort 1 00:00:00:00:00:00:02:00 5",
            "python2 ovxctl.py -n createPort 1 00:00:00:00:00:00:02:00 6",
            "python2 ovxctl.py -n createPort 1 00:00:00:00:00:00:03:00 5",
            "python2 ovxctl.py -n createPort 1 00:00:00:00:00:00:03:00 2",
            # Create virtual links
            "python2 ovxctl.py -n connectLink 1 00:a4:23:05:00:00:00:01 2 00:a4:23:05:00:00:00:02 1 spf 1",
            "python2 ovxctl.py -n connectLink 1 00:a4:23:05:00:00:00:02 2 00:a4:23:05:00:00:00:03 1 spf 1",
            # Connect hosts
            "python2 ovxctl.py -n connectHost 1 00:a4:23:05:00:00:00:01 1 00:00:00:00:01:01",
            "python2 ovxctl.py -n connectHost 1 00:a4:23:05:00:00:00:03 2 00:00:00:00:03:02",
            # Start virtual network
            "python2 ovxctl.py -n startNetwork 1",
        ]
        for cmd in commands:
            ret = check_output(sh_split(cmd), encoding="utf-8")
            print(ret)

        os.chdir(wd)
        CLI(net)

    except Exception as e:
        error(e)
    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    test_ovx()
