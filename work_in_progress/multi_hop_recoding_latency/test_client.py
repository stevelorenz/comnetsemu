#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import time
import socket


class Client(object):
    def __init__(self, server_address):
        self.server_address = server_address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def run(self):
        for _ in range(1000):
            self.sock.sendto(b"Aloha!", server_address)
            time.sleep(1)

    def cleanup(self):
        self.sock.close()


if __name__ == "__main__":
    server_address = ("10.0.3.11", 9999)
    client = Client(server_address)

    try:
        client.run()
    except KeyboardInterrupt as e:
        print("Client stops.")
    finally:
        client.cleanup()
