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
from common import (BUFFER_SIZE, FIELD, GENERATION, META_DATA_LEN, SYMBOL_SIZE,
                    SYMBOLS)


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

    for g in range(GENERATION):
        encoder = encoder_factory.build()
        encoder.set_systematic_on()
        data_in = bytearray(os.urandom(encoder.block_size()))
        symbol_storage = [
            data_in[i:i+SYMBOL_SIZE] for i in range(0, len(data_in), SYMBOL_SIZE)
        ]
        packt_num_gen = 0

        # Send systematic packets
        for _ in range(SYMBOLS):
            rank = encoder.rank()
            encoder.set_const_symbol(rank, symbol_storage[rank])
            payload = encoder.write_payload()
            common.push_metadata(tx_buf, 0, (common.MD_TYPE_DATA, g))
            tx_buf[META_DATA_LEN:META_DATA_LEN+len(payload)] = payload[:]
            sock.sendto(tx_buf[:META_DATA_LEN+len(payload)],
                        (server_ip, server_port))
            packt_num_gen += 1
            packet_num_total += 1
            print("Packet {} of generation {} sent. Rank of encoder: {}".format(
                packt_num_gen, g, rank))
            time.sleep(0.5)

        # Send redundant packets
        for _ in range(redundancy):
            payload = encoder.write_payload()
            common.push_metadata(tx_buf, 0, (common.MD_TYPE_DATA, g))
            tx_buf[META_DATA_LEN:META_DATA_LEN+len(payload)] = payload[:]
            sock.sendto(tx_buf[:META_DATA_LEN+len(payload)],
                        (server_ip, server_port))
            packt_num_gen += 1
            packet_num_total += 1
            print("Packet {} of generation {} sent. Rank of encoder: {}".format(
                packt_num_gen, g, rank))
            time.sleep(0.5)

    sock.close()


if __name__ == "__main__":
    main()
