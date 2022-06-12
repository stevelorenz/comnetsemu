#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""

This module contains utility/helper functions for ComNetsEmu.
"""

import re
import psutil

from mininet.log import error


def parsePing(pingOutput):
    "Parse ping output and return packets sent, received."
    # Check for downed link
    if "connect: Network is unreachable" in pingOutput:
        return 1, 0
    r = r"(\d+) packets transmitted, (\d+)( packets)? received"
    m = re.search(r, pingOutput)
    if m is None:
        error("*** Error: could not parse ping output: %s\n" % pingOutput)
        return 1, 0
    sent, received = int(m.group(1)), int(m.group(2))
    return sent, received


def checkListeningOnPort(port, kind="inet"):
    # net_connections returns a list of system-wide socket connections
    for c in psutil.net_connections(kind=kind):
        # laddr: (ip, port)
        if c.status == "LISTEN" and c.laddr.port == port:
            return True
    return False


def checkListeningOnIPPort(ip, port, kind="inet"):
    for c in psutil.net_connections(kind=kind):
        if c.laddr.ip == ip and c.laddr.port == port and c.status == "LISTEN":
            return True
    return False


def dpidToStr(id: int):
    """Compute a string dpid from the given integer id.

    :param id:
    :type id: int
    :return: The DPID
    :rtype: str
    """
    strDpid = hex(id)[2:]
    if len(strDpid) > 16:
        raise ValueError("Invalid ID. The maximal length of the DPID is 16.")
    if len(strDpid) < 16:
        return "0" * (16 - len(strDpid)) + strDpid
    return strDpid
