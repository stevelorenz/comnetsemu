#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
About: Utility/helper functions for ComNetsEmu.
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


def checkListeningOnPort(port):
    for c in psutil.net_connections(kind="inet"):
        if c.status == "LISTEN" and c.laddr[1] == port:
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
