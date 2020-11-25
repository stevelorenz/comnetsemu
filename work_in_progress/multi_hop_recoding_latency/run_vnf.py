#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import argparse
import shlex
import socket
import subprocess
import sys
import time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["store_forward", "compute_forward"],
        default="store_forward",
        help="The working mode of the current VNF.",
    )
    parser.add_argument(
        "--mem",
        type=int,
        default=50,  # megabytes.
        help="Amount of memory to preallocate at startup.",
    )
    args = parser.parse_args()

    hostname = socket.gethostname()

    if args.mode == "store_forward":
        print("*** Mode: Store and Forward")
    else:
        print("*** Mode: Compute and Forward")

    vnf_fast_path_cmd = ["./build/recoder_vnf"]
    # MARK: Use no-huge for testing, if the performance is not good enough,
    # enable hugepage.
    VNF_FAST_PATH_OPTS = f"-l 1 --proc-type primary \
            -m {args.mem} --no-huge \
            --no-pci --file-prefix={hostname} \
            --vdev net_af_packet0,iface={hostname}-s{hostname[-1]} -- \
            -m {args.mode}"
    vnf_fast_path_cmd.extend(shlex.split(VNF_FAST_PATH_OPTS))
    try:
        subprocess.run(vnf_fast_path_cmd, check=True)
    except KeyboardInterrupt:
        sys.exit(0)
