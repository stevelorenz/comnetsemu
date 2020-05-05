#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
# flake8: noqa
"""
About: Test high-fidelity compatibility between ComNetsEmu and upstream Mininet

Diff upstream test_hifi.py:

- Replace the CPULimitedHost of upstream Mininet's test_hifi with DockerHost.
- Currently only test link delay and loss
- The tolerance is increased because ComNetsEmu is mainly used inside the VM.
  The tolerance is higher than bare-mental setup.
"""

import sys
import unittest
from functools import partial

from comnetsemu.clean import cleanup
from comnetsemu.node import DockerHost
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import IVSSwitch, OVSSwitch, UserSwitch
from mininet.topo import Topo
from mininet.util import quietRun

N = 2

dargs = {"dimage": "dev_test", "dcmd": "bash"}
DockerHostTest = partial(DockerHost, **dargs)


class SingleSwitchOptionsTopo(Topo):
    "Single switch connected to n hosts."

    def __init__(self, n=2, hopts=None, lopts=None):
        if not hopts:
            hopts = {}
        if not lopts:
            lopts = {}
        Topo.__init__(self, hopts=hopts, lopts=lopts)
        switch = self.addSwitch("s1")
        for h in range(n):
            host = self.addHost("h%s" % (h + 1))
            self.addLink(switch, host)


# Tell pylint not to complain about calls to other class
# pylint: disable=E1101


class testOptionsTopoCommon(object):
    """Verify ability to create networks with host and link options
       (common code)."""

    switchClass = None  # overridden in subclasses

    def tearDown(self):
        "Clean up if necessary"
        if sys.exc_info != (None, None, None):
            cleanup()

    def assertWithinTolerance(self, measured, expected, tolerance_frac, msg):
        """Check that a given value is within a tolerance of expected
        tolerance_frac: less-than-1.0 value; 0.8 would yield 20% tolerance.
        """
        upperBound = float(expected) + (1 - tolerance_frac) * float(expected)
        lowerBound = float(expected) * tolerance_frac
        info = (
            "measured value is out of bounds\n"
            "expected value: %s\n"
            "measured value: %s\n"
            "failure tolerance: %s\n"
            "upper bound: %s\n"
            "lower bound: %s\n"
            % (expected, measured, tolerance_frac, upperBound, lowerBound)
        )
        msg += info

        self.assertGreaterEqual(float(measured), lowerBound, msg=msg)
        self.assertLessEqual(float(measured), upperBound, msg=msg)

    def testLinkDelay(self):
        "Verify that link delays are accurate within a bound."
        # ISSUE: Compared to Mininet's default light container, DockerHost is
        # heavier and can not reach a very low latency parameter like 10ms
        DELAY_MS = 100
        DELAY_TOLERANCE = 0.6  # Delay fraction below which test should fail
        REPS = 3
        lopts = {"delay": "%sms" % DELAY_MS, "use_htb": True}
        mn = Mininet(
            topo=SingleSwitchOptionsTopo(n=N, lopts=lopts),
            link=TCLink,
            switch=self.switchClass,
            autoStaticArp=True,
            waitConnected=True,
        )
        mn.start()
        for _ in range(REPS):
            ping_delays = mn.pingFull()
        test_outputs = ping_delays[0]
        # Ignore unused variables below
        # pylint: disable=W0612
        node, dest, ping_outputs = test_outputs
        sent, received, rttmin, rttavg, rttmax, rttdev = ping_outputs
        pingFailMsg = "sent %s pings, only received %s" % (sent, received)
        self.assertEqual(sent, received, msg=pingFailMsg)
        # pylint: enable=W0612
        loptsStr = ", ".join("%s: %s" % (opt, value) for opt, value in lopts.items())
        msg = (
            "\nTesting Link Delay of %s ms\n"
            "ping results across 4 links:\n"
            "(Sent, Received, rttmin, rttavg, rttmax, rttdev)\n"
            "%s\n"
            "Topo = SingleSwitchTopo, %s hosts\n"
            "Link = TCLink\n"
            "lopts = %s\n"
            "host = default"
            "switch = %s\n" % (DELAY_MS, ping_outputs, N, loptsStr, self.switchClass)
        )

        mn.stop()
        for rttval in [rttmin, rttavg, rttmax]:
            # Multiply delay by 4 to cover there & back on two links
            self.assertWithinTolerance(rttval, DELAY_MS * 4.0, DELAY_TOLERANCE, msg)

    def testLinkLoss(self):
        "Verify that we see packet drops with a high configured loss rate."
        LOSS_PERCENT = 99
        REPS = 1
        lopts = {"loss": LOSS_PERCENT, "use_htb": True}
        mn = Mininet(
            topo=SingleSwitchOptionsTopo(n=N, lopts=lopts),
            host=DockerHostTest,
            link=TCLink,
            switch=self.switchClass,
            waitConnected=True,
        )
        # Drops are probabilistic, but the chance of no dropped packets is
        # 1 in 100 million with 4 hops for a link w/99% loss.
        dropped_total = 0
        mn.start()
        for _ in range(REPS):
            dropped_total += mn.ping(timeout="1")
        mn.stop()

        loptsStr = ", ".join("%s: %s" % (opt, value) for opt, value in lopts.items())
        msg = (
            "\nTesting packet loss with %d%% loss rate\n"
            "number of dropped pings during mininet.ping(): %s\n"
            "expected number of dropped packets: 1\n"
            "Topo = SingleSwitchTopo, %s hosts\n"
            "Link = TCLink\n"
            "lopts = %s\n"
            "host = default\n"
            "switch = %s\n"
            % (LOSS_PERCENT, dropped_total, N, loptsStr, self.switchClass)
        )

        self.assertGreater(dropped_total, 0, msg)


# pylint: enable=E1101


class testOptionsTopoOVSKernel(testOptionsTopoCommon, unittest.TestCase):
    """Verify ability to create networks with host and link options
       (OVS kernel switch)."""

    longMessage = True
    switchClass = OVSSwitch


# @unittest.skip('Skipping OVS user switch test for now')
# class testOptionsTopoOVSUser(testOptionsTopoCommon, unittest.TestCase):
#     """Verify ability to create networks with host and link options
#        (OVS user switch)."""
#     longMessage = True
#     switchClass = partial(OVSSwitch, datapath='user')


@unittest.skipUnless(quietRun("which ivs-ctl"), "IVS is not installed")
class testOptionsTopoIVS(testOptionsTopoCommon, unittest.TestCase):
    "Verify ability to create networks with host and link options (IVS)."
    longMessage = True
    switchClass = IVSSwitch


@unittest.skipUnless(
    quietRun("which ofprotocol"), "Reference user switch is not installed"
)
class testOptionsTopoUserspace(testOptionsTopoCommon, unittest.TestCase):
    """Verify ability to create networks with host and link options
     (UserSwitch)."""

    longMessage = True
    switchClass = UserSwitch


if __name__ == "__main__":
    setLogLevel("warning")
    unittest.main(warnings="ignore")
