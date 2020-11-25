#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Data destination, receiver.
"""

import socket


def run():
    server_address = ("10.0.3.11", 9999)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(server_address)

    counter = 0
    while True:
        data, addr = sock.recvfrom(1024)
        counter += 1
        print(f"{counter} Received message: {data.decode()}")


if __name__ == "__main__":
    run()
