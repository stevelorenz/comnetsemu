#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
About: Simple server for counting.
"""

import argparse
import signal
import socket
import time

INTERNAL_IP_H2 = "192.168.0.12"
INTERNAL_IP_H3 = "192.168.0.13"
INTERNAL_PORT = 9999
SERVICE_IP = "10.0.0.12"
SERVICE_PORT = 8888
HOST_NAME = None


def recv_state(host_name):
    """Get the latest counter state from the internal
    network between h2 and h3.
    """
    if host_name == "h2":
        recv_ip = INTERNAL_IP_H2
    else:
        recv_ip = INTERNAL_IP_H3
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((recv_ip, INTERNAL_PORT))

    state, _ = sock.recvfrom(1024)
    state = int(state.decode("utf-8"))
    return state


def run(host_name, get_state=False):
    """Run the couting service and handle sigterm signal."""
    counter = 0
    if get_state:
        counter = recv_state(host_name)
        print("Get the init counter state: {}".format(counter))

    # Use closure to avoid using a global variable for state.
    def term_signal_handler(signum, frame):
        # Check if the server is running on the host 2.
        if host_name == "h2":
            dest_ip = INTERNAL_IP_H3
        else:
            dest_ip = INTERNAL_IP_H2
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Send duplicated packets to avoid losses.
        for _ in range(6):
            sock.sendto(str(counter).encode("utf-8"), (dest_ip, INTERNAL_PORT))
        sock.close()

    signal.signal(signal.SIGTERM, term_signal_handler)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVICE_IP, SERVICE_PORT))

    while True:
        # Block here waiting for data input.
        _, addr = sock.recvfrom(1024)
        counter += 1
        sock.sendto(str(counter).encode("utf-8"), addr)
        time.sleep(0.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple counting server.")
    parser.add_argument(
        "hostname",
        type=str,
        help="The name of the host on which the server is deployed.",
    )
    parser.add_argument(
        "--get_state",
        action="store_true",
        help="Get state from network.",
    )

    args = parser.parse_args()

    run(args.hostname, args.get_state)
