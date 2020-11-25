#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import os
import sys

from comnetsemu.net import Containernet
from mininet.log import info, setLogLevel

PARENT_DIR = os.path.abspath(os.path.join(os.path.curdir, os.pardir))

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Run this script with sudo.", file=sys.stderr)
        sys.exit(1)
    setLogLevel("error")
    print("* Build binaries...")
    try:
        net = Containernet(
            xterms=False,
        )

        builder = net.addDockerHost(
            "builder",
            dimage="kodo_rlnc_coder",
            ip="10.0.1.11/16",
            docker_args={
                "cpuset_cpus": "0",
                "hostname": "builder",
                "volumes": {
                    PARENT_DIR: {"bind": "/kodo_rlnc_coder", "mode": "rw"},
                },
                "working_dir": "/kodo_rlnc_coder/multi_hop_recoding_latency",
            },
        )
        net.start()
        ret = builder.cmd(
            "cd /kodo_rlnc_coder/multi_hop_recoding_latency && make clean && make"
        )
        print(ret)
    finally:
        net.stop()
