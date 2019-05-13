#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Full vector NC encoder
"""

import kodo
import os
import socket
import sys
import time

import common
from common import (BUFFER_SIZE, FIELD, META_DATA_LEN,
                    SYMBOL_SIZE, SYMBOLS)

# number of generations to send
generation = 3


def main():

    if len(sys.argv) > 1:
        server_addr = sys.argv[1]
        server_ip, server_port = server_addr.split(":")[:2]
        server_port = int(server_port)
    else:
        server_ip = "127.0.0.1"
        server_port = 8888

    tx_buf = bytearray(BUFFER_SIZE)
    redundancy = SYMBOLS
    packet_num_total = 0

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Create an encoder factory that are used to build the actual encoders
    encoder_factory = kodo.RLNCEncoderFactory(FIELD, SYMBOLS, SYMBOL_SIZE)
    encoder = encoder_factory.build()

    for g in range(generation):
        data_in = bytearray(os.urandom(encoder.block_size()))
        encoder.set_const_symbols(data_in)

        packt_num_gen = 0
        while packt_num_gen < (SYMBOLS + redundancy):
            payload = encoder.write_payload()
            common.push_metadata(tx_buf, 0, (common.MD_TYPE_DATA, g))
            tx_buf[META_DATA_LEN:META_DATA_LEN+len(payload)] = payload[:]
            sock.sendto(tx_buf[:META_DATA_LEN+len(payload)],
                        (server_ip, server_port))
            packt_num_gen += 1
            packet_num_total += 1
            print("Packet {} of generation {} sent!".format(
                packt_num_gen, g))
            time.sleep(0.5)

    sock.close()


if __name__ == "__main__":
    main()
