#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Forwarding VNF via packet socket.
"""

import argparse
import socket
import sys
import time

IFCE_NAME = "vnf-s1"
BUFFER_SIZE = 4096


def main():
    parser = argparse.ArgumentParser(description="Forwarding VNF")
    parser.add_argument(
        "--max", type=int, default=-1, help="Maximal number of forwarding frames"
    )
    args = parser.parse_args()

    buf = bytearray(BUFFER_SIZE)
    count = 0
    max_count = args.max
    print("*** Maximal forwarding number: {} (-1: infinite)".format(max_count))
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    sock.bind((IFCE_NAME, 0))
    print("*** Packet socket is bind, enter forwarding loop")
    try:
        while True:
            frame_len = sock.recv_into(buf, BUFFER_SIZE)
            count += 1
            if count == max_count:
                print("Reach maximal forwarding number, exits")
                sock.close()
                sys.exit(0)
            time.sleep(0.001)
            sock.send(buf[0:frame_len])
    except KeyboardInterrupt:
        sock.close()
        print("VNF exists.")
        sys.exit(0)


if __name__ == "__main__":
    main()
