#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
About: Simple client.
"""

import socket
import time

SERVICE_IP = "10.0.0.12"
SERVICE_PORT = 8888

if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = b"Show me the counter, please!"

    while True:
        sock.sendto(data, (SERVICE_IP, SERVICE_PORT))
        counter, _ = sock.recvfrom(1024)
        print("Current counter: {}".format(counter.decode("utf-8")))
        time.sleep(1)
